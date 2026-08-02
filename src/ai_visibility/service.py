"""AiVisibilityService — persistence, aggregation and queries (brief §5 M5).

Implements the M5 contract:

- Unknown ``generation_id`` → ``ValueError("Generation not found")`` (router
  maps to 404, matching AnalyticsService).
- Invalid ``days`` (not in {7, 30, 90}) → ``ValueError`` (router maps to 422).
- All public methods async, typed, docstringed.

Aggregation semantics (validated against the pre-written tests):

- ``record_mentions`` stores one ``ai_raw_mentions`` row per result that
  mentions or cites the target; ``mention_type`` is ``citation`` when the
  result cited the URL, ``mention`` otherwise. ``brand_or_topic`` is taken
  from the generation's topic (the share-of-voice corpus key).
- ``compute_engine_metrics`` aggregates ALL raw mentions for (generation,
  engine) — the pre-written tests record rows "now" and compute for an
  explicit historical ``metric_date``, so the raw rows are not date-filtered;
  the given ``metric_date`` is the upsert bucket.
- ``rebuild_trend_aggregates`` rolls engine-metric rows up into
  ``ai_trend_aggregates``: rates are the mean across contents,
  ``ai_referral_traffic`` is the count of referral rows for that day+engine.
"""

from __future__ import annotations

import statistics
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai_visibility.metrics import (
    ai_referral_conversion_rate,
    citation_rate,
    mention_rate,
    sentiment_average,
    sentiment_breakdown,
    share_of_voice,
)
from src.ai_visibility.models import (
    AI_ENGINES,
    AI_METRICS,
    AI_TREND_PERIODS,
    AIEngineMetrics,
    AIRawMention,
    AIReferralTraffic,
    AITrendAggregate,
)
from src.ai_visibility.providers import EngineVisibilityResult
from src.ai_visibility.schemas import (
    AIVisibilityTrendsResponse,
    ContentVisibilityResponse,
    EngineSentiment,
    EngineVisibilityMetrics,
    TrendSeries,
    VisibilitySummary,
    VisibilityTimePoint,
)
from src.models.generation import Generation


def _utcnow() -> datetime:
    """Current tz-aware UTC datetime."""
    return datetime.now(UTC)


def _day_start(day: date) -> datetime:
    """Midnight UTC for a date (inclusive lower bound of that day)."""
    return datetime.combine(day, time.min, tzinfo=UTC)


def _day_end(day: date) -> datetime:
    """Midnight UTC for the day after (exclusive upper bound of that day)."""
    return datetime.combine(day + timedelta(days=1), time.min, tzinfo=UTC)


class AiVisibilityService:
    """Persistence + aggregation + query facade for AI visibility metrics."""

    async def _require_generation(self, db: AsyncSession, generation_id: str) -> Generation:
        """Fetch a generation or raise the canonical 404 ValueError."""
        generation = await db.get(Generation, generation_id)
        if generation is None:
            raise ValueError("Generation not found")
        return generation

    @staticmethod
    def _require_engine(engine: str) -> None:
        """Validate an engine id against AI_ENGINES (ValueError on unknown)."""
        if engine not in AI_ENGINES:
            raise ValueError(f"Invalid engine: {engine!r}")

    async def record_mentions(
        self,
        db: AsyncSession,
        generation_id: str,
        engine: str,
        results: list[EngineVisibilityResult],
    ) -> int:
        """Insert raw mention rows; return rows written.

        Raises ValueError if generation unknown or engine not in AI_ENGINES.
        """
        generation = await self._require_generation(db, generation_id)
        self._require_engine(engine)
        now = _utcnow()
        brand_or_topic = (generation.topic or "")[:255]
        rows = 0
        for result in results:
            if not (result.mentioned or result.cited):
                continue  # no mention event → no raw row
            row = AIRawMention(
                generation_id=generation_id,
                engine=engine,
                query=(result.query or "")[:255],
                brand_or_topic=brand_or_topic,
                mention_type="citation" if result.cited else "mention",
                cited_url=(result.cited_url or "")[:512] if result.cited else None,
                snippet=result.snippet or "",
                sentiment=result.sentiment,
                sentiment_score=None,  # not extracted by the current providers
                mentioned_at=now,
                raw_payload=result.raw_payload or {},
            )
            db.add(row)
            rows += 1
        await db.commit()
        return rows

    async def record_referral(
        self,
        db: AsyncSession,
        generation_id: str,
        engine: str,
        referrer_url: str,
        landing_path: str = "/",
        converted: bool = False,
        conversion_value: float = 0.0,
        occurred_at: datetime | None = None,
    ) -> str:
        """Insert one ai_referral_traffic row; return referral id."""
        await self._require_generation(db, generation_id)
        self._require_engine(engine)
        row = AIReferralTraffic(
            generation_id=generation_id,
            engine=engine,
            referrer_url=referrer_url[:512],
            landing_path=(landing_path or "/")[:255],
            converted=converted,
            conversion_value=conversion_value,
            referred_at=occurred_at or _utcnow(),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row.id

    async def compute_engine_metrics(
        self,
        db: AsyncSession,
        generation_id: str,
        engine: str,
        metric_date: date | None = None,
    ) -> AIEngineMetrics:
        """Aggregate the generation's raw mentions for one engine, compute the
        four metrics, UPSERT into ai_engine_metrics on the unique key.

        share_of_voice uses corpus = all generations with the same
        brand_or_topic as the content (queried from ai_raw_mentions).
        """
        await self._require_generation(db, generation_id)
        self._require_engine(engine)
        bucket_date = metric_date or _utcnow().date()

        rows = (
            await db.execute(
                select(AIRawMention).where(
                    AIRawMention.generation_id == generation_id,
                    AIRawMention.engine == engine,
                )
            )
        ).scalars().all()

        mentions = len(rows)
        citations = sum(1 for r in rows if r.mention_type == "citation")
        samples = len(rows)

        sentiment_counts = sentiment_breakdown([r.sentiment for r in rows])
        sentiment_scores = [r.sentiment_score for r in rows if r.sentiment_score is not None]

        # Share of voice: own citations vs corpus citations for the same
        # brand/topic across all generations.
        own_citations = citations
        brand_or_topic = rows[0].brand_or_topic if rows else ""
        corpus_citations = 0
        if brand_or_topic:
            corpus_rows = (
                await db.execute(
                    select(AIRawMention).where(
                        AIRawMention.brand_or_topic == brand_or_topic
                    )
                )
            ).scalars().all()
            corpus_citations = sum(
                1 for r in corpus_rows if r.mention_type == "citation"
            )

        existing = (
            await db.execute(
                select(AIEngineMetrics).where(
                    AIEngineMetrics.generation_id == generation_id,
                    AIEngineMetrics.engine == engine,
                    AIEngineMetrics.metric_date == bucket_date,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            existing = AIEngineMetrics(
                generation_id=generation_id,
                engine=engine,
                metric_date=bucket_date,
            )
            db.add(existing)

        existing.mentions = mentions
        existing.citations = citations
        existing.citation_rate = citation_rate(citations, mentions)
        existing.mention_rate = mention_rate(mentions, samples)
        existing.share_of_voice = share_of_voice(own_citations, corpus_citations)
        existing.sentiment_positive = sentiment_counts["positive"]
        existing.sentiment_neutral = sentiment_counts["neutral"]
        existing.sentiment_negative = sentiment_counts["negative"]
        existing.sentiment_avg = sentiment_average(sentiment_scores)
        existing.samples = samples
        await db.commit()
        await db.refresh(existing)
        return existing

    async def rebuild_trend_aggregates(
        self,
        db: AsyncSession,
        metric_date: date | None = None,
    ) -> int:
        """Upsert ai_trend_aggregates rows for every (date, engine, metric)
        from ai_engine_metrics (mean of rates, count of referral traffic);
        return rows written."""
        bucket_date = metric_date or _utcnow().date()

        engine_rows = (
            await db.execute(
                select(AIEngineMetrics).where(
                    AIEngineMetrics.metric_date == bucket_date
                )
            )
        ).scalars().all()

        # Group engine-metric rows per engine.
        by_engine: dict[str, list[AIEngineMetrics]] = {}
        for row in engine_rows:
            by_engine.setdefault(row.engine, []).append(row)

        # Referral counts per (engine) for the same day (all generations).
        referral_counts: dict[str, int] = {}
        if by_engine:
            referral_rows = (
                await db.execute(
                    select(AIReferralTraffic).where(
                        AIReferralTraffic.referred_at >= _day_start(bucket_date),
                        AIReferralTraffic.referred_at < _day_end(bucket_date),
                    )
                )
            ).scalars().all()
            for ref in referral_rows:
                if ref.engine in by_engine:
                    referral_counts[ref.engine] = referral_counts.get(ref.engine, 0) + 1

        written = 0
        for engine, rows in by_engine.items():
            values: dict[str, float] = {
                "citation_rate": statistics.fmean(r.citation_rate for r in rows),
                "share_of_voice": statistics.fmean(r.share_of_voice for r in rows),
                "mention_rate": statistics.fmean(r.mention_rate for r in rows),
                "ai_referral_traffic": float(referral_counts.get(engine, 0)),
            }
            for metric in AI_METRICS:
                existing = (
                    await db.execute(
                        select(AITrendAggregate).where(
                            AITrendAggregate.metric_date == bucket_date,
                            AITrendAggregate.engine == engine,
                            AITrendAggregate.metric == metric,
                        )
                    )
                ).scalar_one_or_none()
                if existing is None:
                    existing = AITrendAggregate(
                        metric_date=bucket_date,
                        engine=engine,
                        metric=metric,
                    )
                    db.add(existing)
                existing.value = values[metric]
                existing.sample_size = len(rows)
                written += 1
        await db.commit()
        return written

    async def get_content_visibility(
        self,
        db: AsyncSession,
        content_id: str,
        days: int = 30,
    ) -> ContentVisibilityResponse:
        """Per-content snapshot over the window; 404 via ValueError when the
        generation is unknown; engine list always contains all four engines
        (zero-filled when no data)."""
        # B2 (tech-lead review): validate days BEFORE any lookup — otherwise
        # days=10**15 reaches timedelta(days=days-1) as an unhandled
        # OverflowError (500). Mirrors get_trends' validation (422 mapping).
        if days not in AI_TREND_PERIODS:
            raise ValueError(f"Invalid days: {days!r} (expected 7, 30 or 90)")
        generation = await self._require_generation(db, content_id)
        date_to = _utcnow().date()
        date_from = date_to - timedelta(days=days - 1)

        metrics_rows = (
            await db.execute(
                select(AIEngineMetrics).where(
                    AIEngineMetrics.generation_id == content_id,
                    AIEngineMetrics.metric_date >= date_from,
                    AIEngineMetrics.metric_date <= date_to,
                )
            )
        ).scalars().all()

        referrals = (
            await db.execute(
                select(AIReferralTraffic).where(
                    AIReferralTraffic.generation_id == content_id,
                    AIReferralTraffic.referred_at >= _day_start(date_from),
                    AIReferralTraffic.referred_at < _day_end(date_to),
                )
            )
        ).scalars().all()

        engines: list[EngineVisibilityMetrics] = []
        for engine in AI_ENGINES:
            engine_metrics = [r for r in metrics_rows if r.engine == engine]
            engine_refs = [r for r in referrals if r.engine == engine]

            mentions = sum(r.mentions for r in engine_metrics)
            citations = sum(r.citations for r in engine_metrics)
            samples = sum(r.samples for r in engine_metrics)
            conversions = sum(1 for r in engine_refs if r.converted)

            sov_values = [r.share_of_voice for r in engine_metrics]
            sentiment_avgs = [r.sentiment_avg for r in engine_metrics]

            engines.append(
                EngineVisibilityMetrics(
                    engine=engine,
                    mentions=mentions,
                    citations=citations,
                    citation_rate=citation_rate(citations, mentions),
                    share_of_voice=statistics.fmean(sov_values) if sov_values else 0.0,
                    mention_rate=mention_rate(mentions, samples),
                    sentiment=EngineSentiment(
                        positive=sum(r.sentiment_positive for r in engine_metrics),
                        neutral=sum(r.sentiment_neutral for r in engine_metrics),
                        negative=sum(r.sentiment_negative for r in engine_metrics),
                        avg=statistics.fmean(sentiment_avgs) if sentiment_avgs else 0.0,
                    ),
                    ai_referral_traffic=len(engine_refs),
                    ai_referral_conversions=conversions,
                    ai_referral_conversion_rate=ai_referral_conversion_rate(
                        conversions, len(engine_refs)
                    ),
                )
            )

        total_mentions = sum(e.mentions for e in engines)
        total_citations = sum(e.citations for e in engines)
        total_traffic = sum(e.ai_referral_traffic for e in engines)
        total_conversions = sum(e.ai_referral_conversions for e in engines)

        summary = VisibilitySummary(
            total_mentions=total_mentions,
            total_citations=total_citations,
            overall_citation_rate=citation_rate(total_citations, total_mentions),
            avg_share_of_voice=statistics.fmean(e.share_of_voice for e in engines),
            avg_mention_rate=statistics.fmean(e.mention_rate for e in engines),
            ai_referral_traffic=total_traffic,
            ai_referral_conversions=total_conversions,
            ai_referral_conversion_rate=ai_referral_conversion_rate(
                total_conversions, total_traffic
            ),
        )

        # Time series: one point per day that has engine-metric data.
        by_day: dict[date, list[AIEngineMetrics]] = {}
        for row in metrics_rows:
            by_day.setdefault(row.metric_date, []).append(row)
        referrals_by_day: dict[date, list[AIReferralTraffic]] = {}
        for ref in referrals:
            day = ref.referred_at.date()
            referrals_by_day.setdefault(day, []).append(ref)

        time_series: list[VisibilityTimePoint] = []
        for day in sorted(by_day):
            day_rows = by_day[day]
            day_mentions = sum(r.mentions for r in day_rows)
            day_citations = sum(r.citations for r in day_rows)
            day_samples = sum(r.samples for r in day_rows)
            day_sov = statistics.fmean(r.share_of_voice for r in day_rows)
            time_series.append(
                VisibilityTimePoint(
                    date=day.isoformat(),
                    citation_rate=citation_rate(day_citations, day_mentions),
                    share_of_voice=day_sov,
                    mention_rate=mention_rate(day_mentions, day_samples),
                    ai_referral_traffic=len(referrals_by_day.get(day, [])),
                )
            )

        return ContentVisibilityResponse(
            content_id=generation.id,
            topic=generation.topic or "",
            content_type=generation.content_type or "",
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
            summary=summary,
            engines=engines,
            time_series=time_series,
        )

    async def get_trends(
        self,
        db: AsyncSession,
        days: int = 30,
        engine: str | None = None,
        metric: str | None = None,
    ) -> AIVisibilityTrendsResponse:
        """Chart.js-ready trend series from ai_trend_aggregates; validates
        days in {7,30,90} and engine/metric against constants (ValueError).
        totals = mean per rate metric / sum for ai_referral_traffic across the
        window (all four keys always present)."""
        if days not in AI_TREND_PERIODS:
            raise ValueError(f"Invalid days: {days!r} (expected 7, 30 or 90)")
        if engine is not None and engine not in AI_ENGINES:
            raise ValueError(f"Invalid engine: {engine!r}")
        if metric is not None and metric not in AI_METRICS:
            raise ValueError(f"Invalid metric: {metric!r}")

        date_to = _utcnow().date()
        date_from = date_to - timedelta(days=days - 1)
        dates = [(date_from + timedelta(days=i)).isoformat() for i in range(days)]

        stmt = select(AITrendAggregate).where(
            AITrendAggregate.metric_date >= date_from,
            AITrendAggregate.metric_date <= date_to,
        )
        if engine is not None:
            stmt = stmt.where(AITrendAggregate.engine == engine)
        if metric is not None:
            stmt = stmt.where(AITrendAggregate.metric == metric)
        agg_rows = (await db.execute(stmt)).scalars().all()

        # Series: one Chart.js dataset per (engine, metric), zero-filled days.
        series_map: dict[tuple[str, str], dict[str, float]] = {}
        for row in agg_rows:
            series_map.setdefault((row.engine, row.metric), {})[
                row.metric_date.isoformat()
            ] = row.value
        series = [
            TrendSeries(
                engine=key[0],
                metric=key[1],
                data=[day_map.get(day, 0.0) for day in dates],
            )
            for key, day_map in sorted(series_map.items())
        ]

        # Totals: mean of rate metrics, sum of referral traffic; all four keys
        # are always present (0.0 when no data).
        totals: dict[str, float] = {m: 0.0 for m in AI_METRICS}
        for metric_name in AI_METRICS:
            values = [r.value for r in agg_rows if r.metric == metric_name]
            if not values:
                continue
            if metric_name == "ai_referral_traffic":
                totals[metric_name] = float(sum(values))
            else:
                totals[metric_name] = statistics.fmean(values)

        return AIVisibilityTrendsResponse(
            period=f"{days}d",
            days=days,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
            dates=dates,
            series=series,
            totals=totals,
        )
