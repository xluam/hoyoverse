---
name: questionnaire-briefing
description: Generate polished KPI briefing reports from standardized questionnaire_processed.csv outputs. Use when the user asks for a survey brief, summary, conversion report, underage rate, device eligibility rate, qualified/through user_type mix, T0 rate, T0+T1 rate, HTML report, or related questionnaire performance metrics.
---

# Questionnaire Briefing

Use this skill after `questionnaire-processor` has produced `questionnaire_processed.csv`.

## Workflow

1. Locate the processed CSV. Default to:

```text
C:\Users\xinyi.lu02\Desktop\ai-data-dashboard\outputs\questionnaire_processor\questionnaire_processed.csv
```

2. Run the bundled script:

```powershell
python C:\Users\xinyi.lu02\.codex\skills\questionnaire-briefing\scripts\generate_questionnaire_brief.py `
  --input C:\Users\xinyi.lu02\Desktop\ai-data-dashboard\outputs\questionnaire_processor\questionnaire_processed.csv `
  --output-dir C:\Users\xinyi.lu02\Desktop\ai-data-dashboard\outputs\questionnaire_briefing
```

3. Read `questionnaire_brief.md`, `questionnaire_brief.html`, and `questionnaire_brief_metrics.json` before answering.

The brief should include narrative analysis, not only raw metrics: one-page conclusions, KPI cards in HTML, screening funnel, language breakdown, through-user `user_type` mix, cumulative T0/T1/T2/T3 rates, interpretation, and follow-up checks. In user-facing report text, display `pass = 1` as "通过".

## Metric Definitions

- Total respondents: all rows in the processed CSV.
- Minor respondents: rows where `age_group = 1`.
- Minor rate: minor respondents / total respondents.
- Non-minor respondents: rows where `age_group` is non-empty and not `1`.
- Device eligible non-minor respondents: rows where `device_ok = 1` and `age_group` is non-empty and not `1`.
- Device eligibility rate: device eligible non-minor respondents / non-minor respondents.
- Through respondents: rows where `pass = 1`; display this as "通过" in reports.
- User type mix: compute within through respondents.
- T0 rate: through rows where `user_type = T0` / through respondents.
- T0+T1 rate: through rows where `user_type` is `T0` or `T1` / through respondents.
- T0+T1+T2 rate: through rows where `user_type` is `T0`, `T1`, or `T2` / through respondents.
- T0+T1+T2+T3 rate: through rows where `user_type` is `T0`, `T1`, `T2`, or `T3` / through respondents.

When a denominator is zero, show `N/A` in the Markdown and `null` in JSON for the rate.
