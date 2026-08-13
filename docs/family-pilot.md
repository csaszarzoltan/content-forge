# Family Pilot Guide

## Cohort and ethics

Recruit 5-10 creator households or family-run micro-businesses. Require one adult owner in every session. Teen participation is invited and supervised by the adult; do not recruit younger children into independent accounts. Collect only the participant code, role, task timestamps, success/failure, support interventions, and optional comments. Do not record private drafts, credentials, or provider tokens.

## Session setup

- 60-minute moderated first session plus a 7-day diary.
- Provide a private test workspace and non-public provider accounts.
- Moderator may intervene only after 90 seconds of visible blocking; record each intervention.
- Start timers before showing the relevant screen.

## Tasks and success metrics

1. **First useful draft:** from Family Home to a saved draft containing the intended message. Record minutes. Target median <=10 minutes.
2. **Next-action recognition:** show Home and ask “What would you do next?” Record whether the adult identifies the highlighted next action within 10 seconds. Target >=80%.
3. **Contributor publish boundary:** ask the teen why no Publish action exists. Success requires an explanation that an adult approves/publishes. Target >=90%.
4. **Private versus public:** show an idea, draft, approval, and confirmation. Participant correctly labels all four states. Target >=90%.
5. **Invitation acceptance:** invited member joins without moderator assistance. Target >=80%.
6. **Approve and publish:** adult finds review, approves exact revision, completes final confirmation, and reaches provider result without assistance. Target >=80%.
7. **Connection recovery:** provide one expired/nonconfigured connection. Record interventions and recovery time. Target median <=5 minutes and <=1 intervention.
8. **Time saved:** after seven days, compare self-reported prior weekly time with observed/diary time. Success signal is >=2 hours saved for at least 60% of households; strong signal is >=3 hours.

## Stop conditions

Stop a task immediately if a participant might publish personal/private content, exposes credentials, becomes distressed, or cannot understand public visibility. Reset test data and document the event without retaining sensitive content.

## Pilot result schema

Use `family-pilot-results.csv` with one row per household and these columns:

`participant_code,adult_count,teen_count,first_draft_minutes,next_action_under_10s,teen_understands_publish_boundary,privacy_states_correct,invitation_without_help,approve_publish_without_help,connection_recovery_minutes,connection_support_interventions,prior_weekly_hours,pilot_weekly_hours,hours_saved,critical_incident,notes`

## Go/no-go rule

Proceed from paid beta to broader release only when there are zero critical privacy/publication incidents, every task target is met or has a documented fix, median first draft is <=10 minutes, and at least 60% of households report >=2 hours saved. Otherwise fix the highest-frequency blocking issue and repeat with five new households.
