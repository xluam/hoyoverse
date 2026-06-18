---
name: ua-device-performance
description: Parse Android user-agent data and judge whether devices meet a V9 Android performance baseline. Use when a user provides UA strings, a CSV/XLSX/table containing a ua/user_agent column, or asks for device pass/fail/达标/不达标 results using a V9 Android model mapping workbook such as CB2_安卓设备型号映射表_v9.1_精简版.xlsx.
---

# UA Device Performance

Use this skill to convert Android UA data into a performance judgment document. The preferred deterministic path is the bundled script `scripts/judge_ua_v9.py`.

## Inputs

Accept any of these:

- A CSV with a `ua`, `user_agent`, or `userAgent` column.
- A single UA string.
- A V9 mapping workbook with columns equivalent to: region, device model, product name, Model ID, CPU, RAM, and `v9_综合判定`.

If the V9 workbook is not specified, look first for the latest `CB2_*.xlsx` under:

```text
C:\Users\xinyi.lu02\AppData\Roaming\miHoYo\HoYowave\Shell\File\Downloads
```

## Workflow

1. Locate the UA source and the V9 workbook.
2. Run `scripts/judge_ua_v9.py` with the input file or a single UA.
3. Review the generated Markdown report before answering.
4. Return links to the output CSV/report and summarize counts.

Example for a CSV:

```powershell
python C:\Users\xinyi.lu02\.codex\skills\ua-device-performance\scripts\judge_ua_v9.py `
  --input C:\path\to\ua.csv `
  --v9 C:\path\to\CB2_安卓设备型号映射表_v9.1_精简版.xlsx `
  --output-dir C:\path\to\outputs
```

Example for one UA:

```powershell
python C:\Users\xinyi.lu02\.codex\skills\ua-device-performance\scripts\judge_ua_v9.py `
  --ua "Mozilla/5.0 (Linux; Android 16; 2311DRK48G Build/...)" `
  --v9 C:\path\to\CB2_安卓设备型号映射表_v9.1_精简版.xlsx
```

Use the bundled Python from Codex workspace dependencies when available. Do not install packages; the script only requires the Python standard library plus `openpyxl`, which is present in the Codex bundled runtime.

## Outputs

The script writes:

- `ua_v9_device_performance_matched.csv`: row-level results.
- `ua_v9_device_performance_unmatched_detail.csv`: rows with no V9 judgment.
- `ua_v9_device_performance_unmatched_grouped.csv`: unmatched models grouped by frequency.
- `ua_v9_device_performance_report.md`: concise summary for the user.
- `ua_v9_device_performance_summary.json`: machine-readable counts and samples.

The row-level CSV includes:

```text
ua, ua_android_model, detector_brand, detector_model, detector_device,
v9_综合判定, 是否达标, match_method, matched_by,
v9_region, v9_device_model, v9_product, v9_model_id, v9_cpu, v9_ram,
conflict_statuses
```

## Judgment Rules

- Treat `v9_综合判定 = 达标` as pass.
- Treat `v9_综合判定 = 不达标` as fail.
- Treat `未知`, `未命中`, and `冲突:*` as not deterministically pass; report them separately.
- Prefer exact `Model ID` or raw UA model matches over fuzzy product matches.
- Use Matomo DeviceDetector `mobiles.yml` rules to resolve raw UA model codes to brand/product names before falling back to loose V9 product matching.
- Call out that UA can be spoofed and that PC UA cannot provide CPU/GPU/RAM.

## Known Caveats

- Some `SM-X*` Samsung tablet model codes can be misclassified by generic third-party model patterns; inspect high-volume unmatched rows.
- Some future devices may be parseable by UA code but absent from the V9 workbook; these should become alias/mapping-table additions.
- Android reduced UA values such as `Android 10; K` usually cannot identify a concrete model without Client Hints.
- A suspicious UA can contain conflicting fragments, such as a Samsung model with a Huawei build string. Keep these in unmatched or review buckets rather than forcing a pass.
