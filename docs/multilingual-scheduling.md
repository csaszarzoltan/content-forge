# Multilingual Scheduling — Cross-Language Content Publishing

Schedule, publish, and manage content across multiple languages with timezone-aware delivery, language-specific calendars, and automated cross-posting. Part of the ContentForge multi-language feature set.

## Overview

The multilingual scheduling system extends the existing ContentForge scheduler with language-aware publishing rules. Content can be scheduled in one language and auto-translated for others, published at optimal times per market, and managed through a unified calendar.

Key capabilities:

1. **Timezone-aware scheduling** — Schedule publishing at local-market optimal times, regardless of the operator's timezone.
2. **Language-specific calendars** — Separate publishing calendars per language with independent schedules.
3. **Auto-translate on schedule** — Schedule content in one language and auto-generate translations for other target languages at publish time.
4. **Cross-language dependency** — Define that a German post must publish after the English original, and the Hungarian version after the German.
5. **Publishing window constraints** — Restrict publishing to business hours, weekdays, or specific local holidays per market.

## Architecture

```
contentforge.multilang.scheduling
├── MultilingualScheduler       ← Language-aware scheduling orchestrator
├── TimezoneResolver            ← Market → timezone mapping
├── LanguageCalendar            ← Per-language holiday/business-hour rules
├── CrossLanguagePost           ← Content variant across languages
└── PublishingWindow            ← Constraints per language/market
```

## Usage

### Schedule Content for a Single Language

```python
from datetime import datetime, timezone, timedelta
from contentforge.multilang.scheduling import MultilingualScheduler

scheduler = MultilingualScheduler()

# Schedule a Hungarian blog post for Budapest morning (9:00 CET)
schedule_id = await scheduler.schedule(
    generation_id="gen_a1b2c3d4",
    language="hu",
    publish_at=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc),
    platform="wordpress",
    timezone="Europe/Budapest",  # Publish at 9:00 Budapest time
)
print(f"Scheduled: {schedule_id}")
```

### Schedule Multi-Language Content

```python
# Schedule an English post, then auto-translate to German and Hungarian
schedule = await scheduler.schedule_multilang(
    source_generation_id="gen_a1b2c3d4",
    source_language="en",
    target_languages=["de", "hu"],
    base_publish_at=datetime(2026, 8, 16, 14, 0, tzinfo=timezone.utc),
    stagger_hours=6,  # DE publishes 6h after EN, HU publishes 6h after DE
    platforms={
        "en": ["wordpress", "linkedin"],
        "de": ["wordpress"],
        "hu": ["wordpress", "facebook"],
    },
    timezone_per_language={
        "de": "Europe/Berlin",
        "hu": "Europe/Budapest",
    },
)
print(f"EN: {schedule.entries['en'].schedule_id}")
print(f"DE: {schedule.entries['de'].schedule_id}")
print(f"HU: {schedule.entries['hu'].schedule_id}")
```

### Market-Optimal Publishing

```python
from contentforge.multilang.scheduling import TimezoneResolver, PublishingWindow

resolver = TimezoneResolver()

# Get optimal publishing times by market
markets = resolver.get_optimal_times(
    languages=["en", "de", "hu", "ja"],
    content_type="blog",
)
for market in markets:
    print(f"{market.language:4s} → {market.optimal_hour:02d}:00 {market.timezone} "
          f"(weekday: {market.weekday_only})")

# Output:
# en   → 08:00 America/New_York (weekday: True)
# de   → 10:00 Europe/Berlin   (weekday: True)
# hu   → 09:00 Europe/Budapest (weekday: True)
# ja   → 12:00 Asia/Tokyo      (weekday: False — weekends OK in Japan)
```

### Publishing Windows

```python
from contentforge.multilang.scheduling import PublishingWindow

# Restrict Hungarian publishing to business hours on weekdays
window = PublishingWindow(
    language="hu",
    timezone="Europe/Budapest",
    weekday_only=True,
    hour_start=8,    # 08:00
    hour_end=18,     # 18:00
    holidays=["2026-08-20", "2026-10-23", "2026-11-01"],  # Hungarian holidays
)

# Validate a proposed time
if window.is_allowed(datetime(2026, 8, 20, 9, 0)):
    print("Allowed")     # → NOT allowed (Aug 20 is Hungarian national holiday)
else:
    print("Blocked by holiday or off-hours")
```

### Dependency Chains

```python
# EN must publish first, DE after EN is confirmed, HU after DE
chain_id = await scheduler.create_chain([
    {"language": "en", "generation_id": "gen_111", "publish_at": "2026-08-17T14:00:00Z"},
    {"language": "de", "generation_id": "gen_222", "publish_at": None, "depends_on": "en", "delay_hours": 4},
    {"language": "hu", "generation_id": "gen_333", "publish_at": None, "depends_on": "de", "delay_hours": 2},
])
# DE publishes 4h after EN confirms, HU 2h after DE
```

## Configuration

### `MultilingualSchedulerConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_timezone` | `str` | `"UTC"` | Default timezone for unscheduled markets |
| `stagger_default_hours` | `int` | `6` | Default stagger between language publications |
| `auto_translate_on_schedule` | `bool` | `True` | Auto-translate content when scheduling multi-language posts |
| `respect_holidays` | `bool` | `True` | Skip publishing on local public holidays |
| `max_chain_depth` | `int` | `5` | Maximum cross-language dependency chain depth |
| `publish_retry_count` | `int` | `3` | Retry attempts for failed publishing |

## Data Model

### `MultilingualScheduleEntry`

| Field | Type | Description |
|-------|------|-------------|
| `schedule_id` | `str` | Unique schedule identifier |
| `generation_id` | `str` | Content generation reference |
| `language` | `str` | Target language code |
| `publish_at` | `datetime` | Scheduled publish time (UTC) |
| `timezone` | `str` | Local timezone for display |
| `platform` | `str` | Publishing platform |
| `status` | `str` | `pending`, `published`, `failed`, `cancelled` |
| `depends_on` | `str \| None` | Parent schedule ID in a chain |
| `published_at` | `datetime \| None` | Actual publish time |

## Supported Timezones

The system uses the [IANA Time Zone Database](https://www.iana.org/time-zones) via `pytz` or `zoneinfo` (Python 3.9+). Any IANA timezone string is valid:

```
Europe/Budapest, Europe/Berlin, America/New_York, Asia/Tokyo,
Asia/Shanghai, Australia/Sydney, Pacific/Auckland, ...
```

## Dependencies

Add to `requirements.txt` or `pyproject.toml`:

```
pytz>=2024.1
# Use zoneinfo (stdlib) for Python 3.9+
```

## See Also

- [Language Detection](language-detection.md) — Detecting input language
- [Prompt Templates (per-language)](prompt-templates.md) — Language-adaptive template system
- [Translation Pipeline](translation-pipeline.md) — Quality assessment for cross-language content
