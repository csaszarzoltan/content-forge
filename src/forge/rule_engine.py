"""Content-Forge deterministic channel rule engine (spec §3.2, P0-2).

Enforces per-channel rules WITHOUT any LLM: char limits and hashtag budgets
come from the existing ConstraintRegistry (never hardcoded — spec §5 risk 4),
prohibited phrases come from the brief, and soft rules (required sections,
reading level) come from the brief's OutputConstraints.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field

from src.constraints.registry import ConstraintRegistry
from src.forge.brief_schemas import Brief, OutputConstraints


class RuleSeverity(str, Enum):
    """Violation severity — hard blocks approval/export, soft warns only."""

    hard = "hard"
    soft = "soft"


class RuleViolation(BaseModel):
    """A single rule violation with the offending char spans."""

    rule_id: str  # e.g. "channel.max_chars"
    channel: str
    severity: RuleSeverity
    message: str  # names the violated rule + observed vs limit
    positions: list[tuple[int, int]] = Field(default_factory=list)  # char spans


class ChannelRuleResult(BaseModel):
    """Per-channel evaluation outcome."""

    channel: str
    ok: bool  # True iff no hard violations
    violations: list[RuleViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# Registry platform key for the "x" forge channel (registry data uses "twitter").
_X_REGISTRY_KEY = "twitter"


def _registry_key(channel: str) -> str:
    return _X_REGISTRY_KEY if channel == "x" else channel


class ChannelRuleEngine:
    """Deterministic rule enforcement over a ConstraintRegistry."""

    def __init__(self, registry: ConstraintRegistry | None = None) -> None:
        self._registry = registry

    def _load_registry(self) -> ConstraintRegistry:
        """Lazy-load the repo default registry when none was injected."""
        if self._registry is None:
            registry = ConstraintRegistry()
            registry.load()
            self._registry = registry
        return self._registry

    def evaluate(
        self,
        channel: str,
        text: str,
        constraints: OutputConstraints | None = None,
        prohibited_phrases: list[str] | None = None,
    ) -> ChannelRuleResult:
        """Evaluate all rules for one channel.

        Hard rules: channel char limit (registry), prohibited phrase hits,
        hashtag budget. Soft rules: tone/reading-level keywords absent,
        required sections missing.
        """
        violations: list[RuleViolation] = []
        warnings: list[str] = []
        registry = self._load_registry()
        pc = None

        # -- hard: char limit from the registry (spec §5 risk 4: never hardcode)
        try:
            pc = registry.get(_registry_key(channel))
            max_chars = pc.text.max_chars
            if max_chars and len(text) > max_chars:
                violations.append(
                    RuleViolation(
                        rule_id="channel.max_chars",
                        channel=channel,
                        severity=RuleSeverity.hard,
                        message=(
                            f"channel.max_chars: {len(text)} chars exceeds the "
                            f"{max_chars} char limit for {channel}"
                        ),
                        positions=[(0, len(text))],
                    )
                )
        except KeyError:
            warnings.append(f"no constraint entry for channel '{channel}'")

        # -- hard: prohibited phrase hits (case-insensitive whole-word)
        if prohibited_phrases:
            seen: set[str] = set()
            for phrase in prohibited_phrases:
                phrase = phrase.strip()
                if not phrase or phrase.lower() in seen:
                    continue
                seen.add(phrase.lower())
                spans: list[tuple[int, int]] = []
                pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
                for match in pattern.finditer(text):
                    spans.append((match.start(), match.end()))
                if spans:
                    violations.append(
                        RuleViolation(
                            rule_id="channel.prohibited_phrase",
                            channel=channel,
                            severity=RuleSeverity.hard,
                            message=(
                                f"channel.prohibited_phrase: banned phrase "
                                f"'{phrase}' found in {channel} content"
                            ),
                            positions=spans,
                        )
                    )

        # -- hard: hashtag budget from the registry
        if max_hashtags := (pc.text.max_hashtags if pc else None):
            count = len(re.findall(r"#\w+", text))
            if count > max_hashtags:
                violations.append(
                    RuleViolation(
                        rule_id="channel.max_hashtags",
                        channel=channel,
                        severity=RuleSeverity.hard,
                        message=(
                            f"channel.max_hashtags: {count} hashtags exceeds the "
                            f"{max_hashtags} limit for {channel}"
                        ),
                    )
                )

        # -- soft: required sections missing
        if constraints and constraints.required_sections:
            missing = [
                s for s in constraints.required_sections if s.lower() not in text.lower()
            ]
            if missing:
                violations.append(
                    RuleViolation(
                        rule_id="channel.required_section",
                        channel=channel,
                        severity=RuleSeverity.soft,
                        message=(
                            f"channel.required_section: missing required section(s): "
                            f"{', '.join(missing)}"
                        ),
                    )
                )

        # -- soft: reading-level keywords absent
        if constraints and constraints.reading_level and constraints.keywords:
            missing_kw = [k for k in constraints.keywords if k.lower() not in text.lower()]
            if missing_kw:
                violations.append(
                    RuleViolation(
                        rule_id="channel.reading_level",
                        channel=channel,
                        severity=RuleSeverity.soft,
                        message=(
                            f"channel.reading_level: keywords absent for "
                            f"'{constraints.reading_level}' reading level: "
                            f"{', '.join(missing_kw)}"
                        ),
                    )
                )

        ok = not any(v.severity == RuleSeverity.hard for v in violations)
        return ChannelRuleResult(channel=channel, ok=ok, violations=violations, warnings=warnings)

    def evaluate_all(self, drafts: dict[str, str], brief: Brief) -> dict[str, ChannelRuleResult]:
        """Evaluate every draft channel; key = channel; ok = all channels ok."""
        results: dict[str, ChannelRuleResult] = {}
        for channel, text in drafts.items():
            constraints = brief.output_constraints.get(channel)
            results[channel] = self.evaluate(
                channel,
                text,
                constraints=constraints,
                prohibited_phrases=brief.prohibited_phrases,
            )
        return results


__all__ = ["ChannelRuleEngine", "ChannelRuleResult", "RuleSeverity", "RuleViolation"]
