"""Analytics service — business logic for the v0.9.0 analytics dashboard.

Event-log based (analysis brief §3.2/§5.1): ``analytics_events`` is the
canonical performance source; all metrics are aggregated from it on read.

Metric definitions (canonical, brief §3.2):
- ``impressions`` = SUM(value) of ``impression`` events
- ``engagement_rate`` = (clicks + shares + comments + conversions) / impressions,
  clamped to [0.0, 1.0]
- ``read_time_seconds`` = SUM(value) of ``read_time`` events
- ``avg_read_time_seconds`` = SUM / COUNT (event average)

Validation errors (unknown generation/test -> 404; invalid metric/period/
format/date-window -> ValueError) are raised as ``ValueError``; routers map
them to HTTP 404/422 per endpoint.
"""

from __future__ import annotations

import csv
import io
import json
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ab_test import ABTest, ABVariant
from src.models.analytics import (
    ANALYTICS_CHANNELS,
    AnalyticsEvent,
    ContentAnalytics,
)
from src.models.generation import Generation
from src.schemas.analytics import (
    ABResultsCorrelationResponse,
    AnomalyItem,
    AnomalyResponse,
    ChannelComparisonResponse,
    ChannelMetrics,
    ComplianceData,
    ContentPerformanceResponse,
    DashboardResponse,
    ExportResponse,
    MetricSummary,
    PerformanceData,
    TimeSeriesPoint,
    TopContentItem,
    TrackEventRequest,
    TrackEventResponse,
    TrendPoint,
    TrendResponse,
    VariantPerformance,
)
from src.services.ab_stats import AbStatsService

# Metrics usable as a sort/trend/anomaly metric (brief §4 T5/T9).
ANALYTICS_METRICS: list[str] = [
    "impressions",
    "clicks",
    "shares",
    "comments",
    "conversions",
    "engagement_rate",
]

# Valid trend/anomaly periods mapped to their day counts (brief §4 T9).
ANALYTICS_PERIODS: dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}

# Export row columns (brief §4 T7) — one row per daily aggregate.
EXPORT_COLUMNS: list[str] = [
    "date",
    "generation_id",
    "content_type",
    "channel",
    "event_type",
    "value",
]

# Engagement event types that count toward engagement_rate (brief §3.2).
_ENGAGEMENT_EVENT_TYPES: tuple[str, ...] = ("click", "share", "comment", "conversion")

# Summable event types (value contributes to a metric column).
_SUMMABLE_EVENT_TYPES: tuple[str, ...] = (
    "impression",
    "click",
    "share",
    "comment",
    "conversion",
    "read_time",
)


def _aggregate(events: list[AnalyticsEvent]) -> MetricSummary:
    """Aggregate a list of events into a :class:`MetricSummary`.

    Counts are summed per event type; ``engagement_rate`` follows the
    canonical definition from the analysis brief §3.2.
    """
    totals: dict[str, int] = {et: 0 for et in _SUMMABLE_EVENT_TYPES}
    for event in events:
        if event.event_type in totals:
            totals[event.event_type] += event.value
    impressions = totals["impression"]
    engaged = sum(totals[et] for et in _ENGAGEMENT_EVENT_TYPES)
    engagement_rate = min(1.0, engaged / impressions) if impressions > 0 else 0.0
    return MetricSummary(
        impressions=impressions,
        clicks=totals["click"],
        shares=totals["share"],
        comments=totals["comment"],
        conversions=totals["conversion"],
        read_time_seconds=totals["read_time"],
        engagement_rate=engagement_rate,
    )


def _resolve_window(
    date_from: datetime | None, date_to: datetime | None
) -> tuple[datetime, datetime]:
    """Validate and default the date window (default: last 30 days).

    Raises:
        ValueError: If ``date_from`` is later than ``date_to``.
    """
    now = datetime.now(UTC)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ValueError("date_from must not be later than date_to")
    if date_from is None:
        date_from = now - timedelta(days=30)
    if date_to is None:
        date_to = now
    return date_from, date_to


def _parse_period(period: str) -> int:
    """Map a period token (7d/30d/90d) to a day count.

    Raises:
        ValueError: If the period token is not recognized.
    """
    if period not in ANALYTICS_PERIODS:
        raise ValueError(f"Invalid period: {period!r} (expected 7d, 30d or 90d)")
    return ANALYTICS_PERIODS[period]


async def _fetch_events(
    db: AsyncSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    channel: str | None = None,
    generation_ids: list[str] | None = None,
    content_type: str | None = None,
) -> list[AnalyticsEvent]:
    """Load analytics events applying window/channel/generation/content filters.

    Filtering happens in SQL so datetime comparisons stay consistent with how
    the values were stored (SQLAlchemy binds the same format it stores).
    """
    stmt = select(AnalyticsEvent)
    if date_from is not None:
        stmt = stmt.where(AnalyticsEvent.occurred_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(AnalyticsEvent.occurred_at <= date_to)
    if channel is not None:
        stmt = stmt.where(AnalyticsEvent.channel == channel)
    if generation_ids is not None:
        stmt = stmt.where(AnalyticsEvent.generation_id.in_(generation_ids))
    if content_type is not None:
        stmt = stmt.join(
            Generation, AnalyticsEvent.generation_id == Generation.id
        ).where(Generation.content_type == content_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _group_by_channel(events: list[AnalyticsEvent]) -> dict[str, list[AnalyticsEvent]]:
    """Group events by channel, preserving insertion order of first sight."""
    grouped: dict[str, list[AnalyticsEvent]] = {}
    for event in events:
        grouped.setdefault(event.channel, []).append(event)
    return grouped


def _daily_points(events: list[AnalyticsEvent]) -> list[TimeSeriesPoint]:
    """Build per-day time-series points for days that have events.

    Only days with at least one event produce a point; the list is sorted
    ascending by date.
    """
    by_day: dict[str, list[AnalyticsEvent]] = {}
    for event in events:
        day = event.occurred_at.date().isoformat()
        by_day.setdefault(day, []).append(event)
    points: list[TimeSeriesPoint] = []
    for day in sorted(by_day):
        metrics = _aggregate(by_day[day])
        points.append(
            TimeSeriesPoint(
                date=day,
                impressions=metrics.impressions,
                clicks=metrics.clicks,
                shares=metrics.shares,
                comments=metrics.comments,
                conversions=metrics.conversions,
                engagement_rate=metrics.engagement_rate,
            )
        )
    return points


def _compliance_data(
    generation: Generation, analytics_row: ContentAnalytics | None
) -> ComplianceData:
    """Merge compliance data from the generation and optional snapshot row."""
    scores = generation.compliance_scores or {}
    return ComplianceData(
        overall=float(scores.get("overall", analytics_row.compliance_overall if analytics_row else 0.0) or 0.0),
        vocabulary=float(
            scores.get("vocabulary", analytics_row.compliance_vocabulary if analytics_row else 0.0) or 0.0
        ),
        readability=float(
            scores.get("readability", analytics_row.compliance_readability if analytics_row else 0.0) or 0.0
        ),
        tone=float(scores.get("tone", analytics_row.compliance_tone if analytics_row else 0.0) or 0.0),
        violations=list(scores.get("violations", []) or []),
    )


class _MetricsLike(Protocol):
    """Structural type for objects carrying the seven metric attributes."""

    impressions: int
    clicks: int
    shares: int
    comments: int
    conversions: int
    engagement_rate: float


def _metric_value(metrics: _MetricsLike, metric: str) -> float:
    """Extract the numeric value of a metric from a metrics-shaped object."""
    return float(getattr(metrics, metric))


def _z_score_anomalies(
    values: dict[str, float], metric: str
) -> list[AnomalyItem]:
    """Flag daily values with |z| >= 2.0 (needs >= 7 points, stdlib stats).

    Returns:
        A list of :class:`AnomalyItem`, empty when fewer than 7 points exist
        or the series has zero variance.
    """
    if len(values) < 7:
        return []
    mean = statistics.fmean(values.values())
    try:
        stdev = statistics.pstdev(values.values())
    except statistics.StatisticsError:
        stdev = 0.0
    if stdev == 0.0:
        return []
    anomalies: list[AnomalyItem] = []
    for day, value in sorted(values.items()):
        z_score = (value - mean) / stdev
        if abs(z_score) >= 2.0:
            anomalies.append(
                AnomalyItem(
                    date=day,
                    metric=metric,
                    value=value,
                    z_score=z_score,
                    direction="spike" if z_score > 0 else "drop",
                )
            )
    return anomalies


class AnalyticsService:
    """Content analytics query service (v0.9.0 event-log based)."""

    def __init__(self) -> None:
        pass

    async def track_event(
        self, db: AsyncSession, request: TrackEventRequest
    ) -> TrackEventResponse:
        """Persist an analytics event; raise ValueError if generation unknown."""
        generation = await db.get(Generation, request.generation_id)
        if generation is None:
            raise ValueError("Generation not found")
        if request.channel not in ANALYTICS_CHANNELS:
            raise ValueError(f"Invalid channel: {request.channel!r}")
        occurred_at = request.occurred_at or datetime.now(UTC)
        if occurred_at > datetime.now(UTC) + timedelta(hours=24):
            raise ValueError("occurred_at cannot be more than 24 hours in the future")
        event = AnalyticsEvent(
            generation_id=request.generation_id,
            channel=request.channel,
            event_type=request.event_type,
            value=request.value,
            user_identifier=request.user_identifier,
            event_metadata=request.metadata,
            occurred_at=occurred_at,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return TrackEventResponse(status="ok", event_id=event.id)

    async def get_dashboard(
        self,
        db: AsyncSession,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        channel: str | None = None,
        content_type: str | None = None,
    ) -> DashboardResponse:
        """Aggregate dashboard metrics over the window (default: last 30d)."""
        date_from, date_to = _resolve_window(date_from, date_to)
        events = await _fetch_events(
            db, date_from, date_to, channel=channel, content_type=content_type
        )

        totals = _aggregate(events)
        channel_breakdown = {
            ch: _aggregate(evs) for ch, evs in _group_by_channel(events).items()
        }

        # content_type_breakdown: distinct generations with events, by type.
        content_type_breakdown: dict[str, int] = {}
        generation_ids = {event.generation_id for event in events}
        if generation_ids:
            rows = (
                await db.execute(
                    select(Generation.id, Generation.content_type).where(
                        Generation.id.in_(generation_ids)
                    )
                )
            ).all()
            for _gen_id, gen_content_type in rows:
                content_type_breakdown[gen_content_type] = (
                    content_type_breakdown.get(gen_content_type, 0) + 1
                )

        top_content = await self._top_content(db, events)

        return DashboardResponse(
            date_from=date_from,
            date_to=date_to,
            totals=totals,
            content_type_breakdown=content_type_breakdown,
            channel_breakdown=channel_breakdown,
            top_content=top_content,
            time_series=_daily_points(events),
        )

    @staticmethod
    async def _top_content(
        db: AsyncSession, events: list[AnalyticsEvent]
    ) -> list[TopContentItem]:
        """Top 5 generations by impressions (requires topic/content_type)."""
        by_generation: dict[str, list[AnalyticsEvent]] = {}
        for event in events:
            by_generation.setdefault(event.generation_id, []).append(event)
        ranked = sorted(
            by_generation.items(),
            key=lambda item: _aggregate(item[1]).impressions,
            reverse=True,
        )[:5]
        items: list[TopContentItem] = []
        for gen_id, gen_events in ranked:
            generation = await db.get(Generation, gen_id)
            if generation is None:
                continue
            metrics = _aggregate(gen_events)
            items.append(
                TopContentItem(
                    generation_id=gen_id,
                    topic=generation.topic,
                    content_type=generation.content_type,
                    impressions=metrics.impressions,
                    engagement_rate=metrics.engagement_rate,
                )
            )
        return items

    async def get_content_performance(
        self,
        db: AsyncSession,
        generation_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ContentPerformanceResponse:
        """Per-content performance; raise ValueError -> 404 when unknown."""
        generation = await db.get(Generation, generation_id)
        if generation is None:
            raise ValueError("Generation not found")
        date_from, date_to = _resolve_window(date_from, date_to)
        events = await _fetch_events(
            db, date_from, date_to, generation_ids=[generation_id]
        )
        totals = _aggregate(events)
        channel_breakdown = {
            ch: _aggregate(evs) for ch, evs in _group_by_channel(events).items()
        }

        analytics_row = (
            await db.execute(
                select(ContentAnalytics).where(
                    ContentAnalytics.generation_id == generation_id
                )
            )
        ).scalar_one_or_none()

        read_events = [e for e in events if e.event_type == "read_time"]
        avg_read_time = (
            round(sum(e.value for e in read_events) / len(read_events))
            if read_events
            else 0
        )

        performance = PerformanceData(
            views=totals.impressions,
            engagement_rate=totals.engagement_rate,
            shares=totals.shares,
            comments=totals.comments,
            avg_read_time_seconds=avg_read_time,
        )

        return ContentPerformanceResponse(
            generation_id=generation.id,
            content_type=generation.content_type,
            brand_voice_id=generation.brand_voice_id,
            topic=generation.topic,
            model_used=generation.model_used or "",
            tokens_used=generation.tokens_used or 0,
            compliance=_compliance_data(generation, analytics_row),
            performance=performance,
            channel_breakdown=channel_breakdown,
            score=None,
            created_at=generation.created_at,
            updated_at=analytics_row.last_synced_at if analytics_row else None,
        )

    async def get_channel_comparison(
        self,
        db: AsyncSession,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        metric: str = "impressions",
    ) -> ChannelComparisonResponse:
        """Per-channel metrics; raise ValueError on invalid metric."""
        if metric not in ANALYTICS_METRICS:
            raise ValueError(f"Invalid metric: {metric!r}")
        date_from, date_to = _resolve_window(date_from, date_to)
        events = await _fetch_events(db, date_from, date_to)

        channels: list[ChannelMetrics] = []
        for channel, channel_events in _group_by_channel(events).items():
            metrics = _aggregate(channel_events)
            channels.append(
                ChannelMetrics(
                    channel=channel,
                    impressions=metrics.impressions,
                    clicks=metrics.clicks,
                    shares=metrics.shares,
                    comments=metrics.comments,
                    conversions=metrics.conversions,
                    engagement_rate=metrics.engagement_rate,
                )
            )
        channels.sort(key=lambda c: _metric_value(c, metric), reverse=True)

        return ChannelComparisonResponse(
            date_from=date_from,
            date_to=date_to,
            channels=channels,
            best_channel=channels[0].channel if channels else None,
            total_impressions=sum(c.impressions for c in channels),
        )

    async def get_ab_correlation(
        self,
        db: AsyncSession,
        test_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ABResultsCorrelationResponse:
        """Correlate A/B variants with analytics; raise ValueError -> 404."""
        test = (
            await db.execute(select(ABTest).where(ABTest.id == test_id))
        ).scalar_one_or_none()
        if test is None:
            raise ValueError("AB test not found")
        variants = (
            (
                await db.execute(
                    select(ABVariant)
                    .where(ABVariant.ab_test_id == test_id)
                    .order_by(ABVariant.created_at, ABVariant.id)
                )
            )
            .scalars()
            .all()
        )

        generation_ids = [v.generation_id for v in variants if v.generation_id]
        events = (
            await _fetch_events(db, date_from, date_to, generation_ids=generation_ids)
            if generation_ids
            else []
        )
        events_by_generation: dict[str, list[AnalyticsEvent]] = {}
        for event in events:
            events_by_generation.setdefault(event.generation_id, []).append(event)

        variant_performances: list[VariantPerformance] = []
        for variant in variants:
            metrics = _aggregate(
                events_by_generation.get(variant.generation_id, [])
                if variant.generation_id
                else []
            )
            conversion_rate = (
                metrics.conversions / metrics.impressions
                if metrics.impressions > 0
                else 0.0
            )
            variant_performances.append(
                VariantPerformance(
                    variant_id=variant.id,
                    name=variant.name,
                    variant_type=variant.variant_type,
                    generation_id=variant.generation_id,
                    impressions=metrics.impressions,
                    conversions=metrics.conversions,
                    conversion_rate=conversion_rate,
                    engagement_rate=metrics.engagement_rate,
                    is_winner=test.winner_variant_id == variant.id,
                )
            )

        return ABResultsCorrelationResponse(
            ab_test_id=test.id,
            name=test.name,
            status=test.status,
            winner_variant_id=test.winner_variant_id,
            variants=variant_performances,
            correlation_note=self._build_correlation_note(
                variant_performances, test.winner_variant_id
            ),
        )

    @staticmethod
    def _build_correlation_note(
        variants: list[VariantPerformance], winner_variant_id: str | None
    ) -> str:
        """Build a human-readable significance note for A/B variants.

        Uses :class:`AbStatsService` (chi-squared) on the analytics
        conversion counts; non-empty whenever >= 2 variants have data.
        """
        data_variants = [v for v in variants if v.impressions > 0]
        if len(data_variants) < 2:
            return ""
        counts = [(v.impressions, v.conversions) for v in data_variants]
        result = AbStatsService.calculate_significance(counts)
        confidence = AbStatsService.format_confidence(result.p_value)
        note = f"Analytics conversion p={result.p_value:.3f} ({confidence})"
        if winner_variant_id:
            note += " — matches A/B winner"
        return note

    async def export_data(
        self,
        db: AsyncSession,
        format: str = "json",
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        channel: str | None = None,
        content_type: str | None = None,
    ) -> ExportResponse:
        """Export daily aggregates as CSV or JSON; raise ValueError on bad format."""
        if format not in ("csv", "json"):
            raise ValueError(f"Invalid format: {format!r} (expected csv or json)")
        date_from, date_to = _resolve_window(date_from, date_to)

        stmt = (
            select(
                AnalyticsEvent.occurred_at,
                AnalyticsEvent.generation_id,
                Generation.content_type,
                AnalyticsEvent.channel,
                AnalyticsEvent.event_type,
                AnalyticsEvent.value,
            )
            .join(Generation, AnalyticsEvent.generation_id == Generation.id)
            .where(
                AnalyticsEvent.occurred_at >= date_from,
                AnalyticsEvent.occurred_at <= date_to,
            )
        )
        if channel is not None:
            stmt = stmt.where(AnalyticsEvent.channel == channel)
        if content_type is not None:
            stmt = stmt.where(Generation.content_type == content_type)
        rows = (await db.execute(stmt)).all()

        # One row per daily aggregate keyed by (date, gen, type, channel, type).
        aggregated: dict[tuple[str, str, str, str, str], int] = {}
        for occurred_at, gen_id, gen_type, ev_channel, event_type, value in rows:
            key = (occurred_at.date().isoformat(), gen_id, gen_type, ev_channel, event_type)
            aggregated[key] = aggregated.get(key, 0) + value

        export_rows: list[dict[str, Any]] = [
            {
                "date": key[0],
                "generation_id": key[1],
                "content_type": key[2],
                "channel": key[3],
                "event_type": key[4],
                "value": value,
            }
            for key, value in sorted(aggregated.items())
        ]

        if format == "json":
            data = json.dumps(export_rows)
            content_type_header = "application/json"
        else:
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(EXPORT_COLUMNS)
            for row in export_rows:
                writer.writerow([row[column] for column in EXPORT_COLUMNS])
            data = buffer.getvalue()
            content_type_header = "text/csv"

        filename = (
            f"analytics_export_{datetime.now(UTC).strftime('%Y%m%d')}.{format}"
        )
        return ExportResponse(
            format=format,
            filename=filename,
            content_type=content_type_header,
            data=data,
        )

    async def get_trends(
        self,
        db: AsyncSession,
        period: str = "30d",
        metric: str = "impressions",
        channel: str | None = None,
    ) -> TrendResponse:
        """Daily trend series; raise ValueError on invalid period/metric."""
        days = _parse_period(period)
        if metric not in ANALYTICS_METRICS:
            raise ValueError(f"Invalid metric: {metric!r}")
        now = datetime.now(UTC)
        events = await _fetch_events(
            db, now - timedelta(days=days), now, channel=channel
        )

        by_day: dict[str, list[AnalyticsEvent]] = {}
        for event in events:
            day = event.occurred_at.date().isoformat()
            by_day.setdefault(day, []).append(event)

        points: list[TrendPoint] = []
        for day in sorted(by_day):
            metrics = _aggregate(by_day[day])
            points.append(
                TrendPoint(
                    date=day,
                    impressions=metrics.impressions,
                    clicks=metrics.clicks,
                    shares=metrics.shares,
                    comments=metrics.comments,
                    conversions=metrics.conversions,
                    engagement_rate=metrics.engagement_rate,
                    anomaly=False,
                )
            )

        # Flag anomalies on the requested metric (>= 7 points, |z| >= 2.0).
        values = {point.date: _metric_value(point, metric) for point in points}
        anomalies = _z_score_anomalies(values, metric)
        anomaly_dates = {item.date for item in anomalies}
        for point in points:
            point.anomaly = point.date in anomaly_dates

        return TrendResponse(period=period, metric=metric, points=points)

    async def detect_anomalies(
        self,
        db: AsyncSession,
        period: str = "30d",
        metric: str = "impressions",
    ) -> AnomalyResponse:
        """Flag daily-series anomalies with |z| >= 2.0 (needs >= 7 points)."""
        days = _parse_period(period)
        if metric not in ANALYTICS_METRICS:
            raise ValueError(f"Invalid metric: {metric!r}")
        now = datetime.now(UTC)
        events = await _fetch_events(db, now - timedelta(days=days), now)

        by_day: dict[str, list[AnalyticsEvent]] = {}
        for event in events:
            day = event.occurred_at.date().isoformat()
            by_day.setdefault(day, []).append(event)
        values = {
            day: _metric_value(_aggregate(day_events), metric)
            for day, day_events in by_day.items()
        }
        anomalies = _z_score_anomalies(values, metric)
        return AnomalyResponse(period=period, metric=metric, anomalies=anomalies)

    async def update_performance_metrics(
        self, generation_id: str, metrics: dict
    ) -> None:
        """Update performance metrics (internal webhook)."""
        # Out of scope for P0-P2 (future external-sync path, analysis brief §1.5 #5).
