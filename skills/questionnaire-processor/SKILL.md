---
name: questionnaire-processor
description: Process multilingual questionnaire CSV exports from en/jp/kr/cht survey files into one standardized 46-column CSV. Use when the user asks to clean, merge, standardize, or classify these survey exports, including age grouping, game/user-type classification, pass flags, and Android device eligibility via the ua-device-performance skill.
---

# Questionnaire Processor

Use this skill to process the four questionnaire CSV exports under a downloads folder. The language is the CSV file stem, such as `en`, `jp`, `kr`, or `cht`.

## Workflow

1. Confirm the input directory, defaulting to:

```text
C:\Users\xinyi.lu02\echoworkspace\downloads
```

2. Run the bundled script:

```powershell
python C:\Users\xinyi.lu02\.codex\skills\questionnaire-processor\scripts\process_questionnaires.py `
  --input-dir C:\Users\xinyi.lu02\echoworkspace\downloads `
  --output-dir C:\Users\xinyi.lu02\Desktop\ai-data-dashboard\outputs\questionnaire_processor
```

3. If Android rows are present, the script calls:

```text
C:\Users\xinyi.lu02\.codex\skills\ua-device-performance\scripts\judge_ua_v9.py
```

Use the Codex bundled Python runtime when available. Pass `--v9 path\to\CB2_*.xlsx` if the V9 workbook is not in the default ua-device-performance location. Pass `--matomo-rules path\to\matomo_mobiles.yml` when a cached Matomo rules file is available and network is restricted.

4. Review `questionnaire_processing_report.json` for skipped files, warnings, row counts, and output paths before answering.

## Output

The main output is `questionnaire_processed.csv` with exactly these 46 columns:

```text
id,lang,user_agent,ip_area,age,gender,Android,ios,PC,ios_model,qc4,phone_player,PC_player,console_player,non-player,pokemon_go,pokemon_tcg_pocket,monster_hunter_now,afk_arena,marvel_snap,dragon_ball_z_dokkan_battle,dragon_ball_legends,love_and_deepspace,genshin_impact,honkai_star_rail,zenless_zone_zero,honkai_impact_3rd,cookie_run_kingdom,puzzle_and_dragons,yokai_watch,uma_musume,pokemon_sword_shield,pokemon_scarlet_violet,pokemon_legends_za,pokemon_pokopia,animal_crossing,naruto_clash_of_ninja_2,wuthering_waves,final_fantasy,palworld,email,googleplay,age_group,device_ok,user_type,pass
```

## Core Rules

- Match source columns by question prefix. For example, `q3_1_Android端末` and `q3_1_안드로이드 기기` both map to `Android`.
- Skip survey metadata rows where `id` is like `L1`.
- Compute `age` as `q1 - 1`; when `q1 = 46`, output `45+`.
- For `age_group`, use `<18`, `18-22`, `23-26`, `27-30`, `31-35`, `36+` for `en`, `jp`, and `cht`; for `kr`, use `<19`, `19-22`, then the same remaining bands.
- Set `device_ok = 1` when Android or ios eligibility passes. Android eligibility comes from ua-device-performance and must use `origin_user_agent` first, falling back to `user_agent` only when `origin_user_agent` is blank. ios eligibility passes only when `q4` is one of `1`, `2`, `4`, or `6`.
- Set `pass = 1` only when `device_ok = 1` and `age_group != 1`.
- Classify `user_type` by priority `T0`, `T1`, `T2`, `T3`, otherwise `others`.

## User Type Matrix

Target games are `pokemon_go` and `pokemon_tcg_pocket` for every language. For `kr`, also include `cookie_run_kingdom`.

Mihoyo games are:

```text
genshin_impact,honkai_star_rail,zenless_zone_zero,honkai_impact_3rd
```

Apply priority:

- `T0`: any target game is `4`, and all four Mihoyo games are `1`.
- `T1`: any target game is `3`, and all four Mihoyo games are `1`.
- `T2`: any target game is `4`, and all four Mihoyo games are `<= 2`.
- `T3`: any target game is `3`, and all four Mihoyo games are `<= 2`.
- `others`: target games are below `3`, a Mihoyo game is `>= 3`, values are missing, or no matrix row matches. Empty values are not treated as unplayed.
