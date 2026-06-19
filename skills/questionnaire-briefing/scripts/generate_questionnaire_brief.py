#!/usr/bin/env python
"""Generate a polished questionnaire briefing from questionnaire_processed.csv."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


DEFAULT_INPUT = Path(r"C:\Users\xinyi.lu02\Desktop\ai-data-dashboard\outputs\questionnaire_processor\questionnaire_processed.csv")
DEFAULT_OUTPUT_DIR = Path(r"C:\Users\xinyi.lu02\Desktop\ai-data-dashboard\outputs\questionnaire_briefing")
USER_TYPE_ORDER = ["T0", "T1", "T2", "T3", "others"]


def read_rows(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_rate(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def pct(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


def count_rate(count: int, denominator: int) -> str:
    return f"{count}/{denominator} ({pct(safe_rate(count, denominator))})"


def row_value(row: dict, column: str) -> str:
    return str(row.get(column, "")).strip()


def user_type_distribution(rows: List[dict]) -> Dict[str, int]:
    counts = Counter(row_value(row, "user_type") or "blank" for row in rows)
    ordered = {key: counts.get(key, 0) for key in USER_TYPE_ORDER if counts.get(key, 0)}
    ordered.update({key: value for key, value in counts.items() if key not in USER_TYPE_ORDER})
    return ordered


def compute_metrics(rows: List[dict]) -> Dict:
    total = len(rows)
    minor_rows = [row for row in rows if row_value(row, "age_group") == "1"]
    age_unknown_rows = [row for row in rows if not row_value(row, "age_group")]
    non_minor_rows = [row for row in rows if row_value(row, "age_group") and row_value(row, "age_group") != "1"]
    device_ok_non_minor_rows = [row for row in non_minor_rows if row_value(row, "device_ok") == "1"]
    through_rows = [row for row in rows if row_value(row, "pass") == "1"]
    through_count = len(through_rows)
    user_type_counts = Counter(row_value(row, "user_type") or "blank" for row in through_rows)
    lang_counts = Counter(row_value(row, "lang") or "blank" for row in rows)

    cumulative_specs = {
        "T0": ["T0"],
        "T0+T1": ["T0", "T1"],
        "T0+T1+T2": ["T0", "T1", "T2"],
        "T0+T1+T2+T3": ["T0", "T1", "T2", "T3"],
    }
    cumulative = {}
    for label, types in cumulative_specs.items():
        count = sum(user_type_counts.get(t, 0) for t in types)
        cumulative[label] = {"types": types, "count": count, "rate": safe_rate(count, through_count)}

    language_breakdown = {}
    for lang in sorted(lang_counts):
        lang_rows = [row for row in rows if (row_value(row, "lang") or "blank") == lang]
        lang_total = len(lang_rows)
        lang_minor = [row for row in lang_rows if row_value(row, "age_group") == "1"]
        lang_age_unknown = [row for row in lang_rows if not row_value(row, "age_group")]
        lang_non_minor = [row for row in lang_rows if row_value(row, "age_group") and row_value(row, "age_group") != "1"]
        lang_device_ok_non_minor = [row for row in lang_non_minor if row_value(row, "device_ok") == "1"]
        lang_through = [row for row in lang_rows if row_value(row, "pass") == "1"]
        language_breakdown[lang] = {
            "total": lang_total,
            "share_of_total": safe_rate(lang_total, total),
            "minor": len(lang_minor),
            "minor_rate": safe_rate(len(lang_minor), lang_total),
            "age_unknown": len(lang_age_unknown),
            "age_unknown_rate": safe_rate(len(lang_age_unknown), lang_total),
            "non_minor": len(lang_non_minor),
            "device_ok_non_minor": len(lang_device_ok_non_minor),
            "device_ok_rate_over_non_minor": safe_rate(len(lang_device_ok_non_minor), len(lang_non_minor)),
            "through": len(lang_through),
            "through_rate_over_total": safe_rate(len(lang_through), lang_total),
            "through_user_type_counts": user_type_distribution(lang_through),
        }

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "total_respondents": total,
        "minor_respondents": len(minor_rows),
        "minor_rate": safe_rate(len(minor_rows), total),
        "age_unknown_respondents": len(age_unknown_rows),
        "age_unknown_rate": safe_rate(len(age_unknown_rows), total),
        "non_minor_respondents": len(non_minor_rows),
        "device_ok_non_minor_respondents": len(device_ok_non_minor_rows),
        "device_ok_rate_over_non_minor": safe_rate(len(device_ok_non_minor_rows), len(non_minor_rows)),
        "through_respondents": through_count,
        "through_rate_over_total": safe_rate(through_count, total),
        "through_rate_over_non_minor": safe_rate(through_count, len(non_minor_rows)),
        "language_counts": dict(lang_counts),
        "language_breakdown": language_breakdown,
        "through_user_type_counts": user_type_distribution(through_rows),
        "through_user_type_rates": {
            key: safe_rate(user_type_counts.get(key, 0), through_count)
            for key in USER_TYPE_ORDER
            if user_type_counts.get(key, 0)
        },
        "through_user_type_cumulative": cumulative,
    }


def md_table(headers: List[str], rows: List[List[str]]) -> List[str]:
    aligns = ["---"] + ["---:" for _ in headers[1:]]
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(aligns) + " |",
        *["| " + " | ".join(row) + " |" for row in rows],
    ]


def insight_lines(metrics: Dict) -> List[str]:
    through = metrics["through_respondents"]
    t0 = metrics["through_user_type_cumulative"]["T0"]
    t01 = metrics["through_user_type_cumulative"]["T0+T1"]
    t0123 = metrics["through_user_type_cumulative"]["T0+T1+T2+T3"]
    others = metrics["through_user_type_counts"].get("others", 0)

    lines = [
        f"当前样本共 {metrics['total_respondents']} 人，未成年 {metrics['minor_respondents']} 人，未成年率为 {pct(metrics['minor_rate'])}。",
        f"年龄分组缺失 {metrics['age_unknown_respondents']} 人，占 {pct(metrics['age_unknown_rate'])}；这部分样本不会进入非未成年分母，也不会计入最终通过。",
        f"可确认非未成年样本为 {metrics['non_minor_respondents']} 人，其中设备达标且非未成年 {metrics['device_ok_non_minor_respondents']} 人，设备达标率为 {pct(metrics['device_ok_rate_over_non_minor'])}。",
        f"最终通过 {through} 人，占总样本 {pct(metrics['through_rate_over_total'])}，占可确认非未成年样本 {pct(metrics['through_rate_over_non_minor'])}。",
    ]
    if through:
        lines.append(f"通过人群中 T0 为 {t0['count']} 人，T0 率 {pct(t0['rate'])}；T0+T1 为 {t01['count']} 人，T0+T1 率 {pct(t01['rate'])}。")
        lines.append(f"T0-T3 合计 {t0123['count']} 人，占通过人群 {pct(t0123['rate'])}；others 为 {others} 人，占 {pct(safe_rate(others, through))}。")
    return lines


def render_markdown(metrics: Dict, source: Path) -> str:
    funnel_rows = [
        ["总样本", str(metrics["total_respondents"]), "100.0%", "处理后 CSV 全部行"],
        ["未成年", str(metrics["minor_respondents"]), pct(metrics["minor_rate"]), "`age_group = 1`"],
        ["年龄未知", str(metrics["age_unknown_respondents"]), pct(metrics["age_unknown_rate"]), "`age_group` 为空，不进入非未成年分母"],
        ["可确认非未成年", str(metrics["non_minor_respondents"]), pct(safe_rate(metrics["non_minor_respondents"], metrics["total_respondents"])), "`age_group` 非空且不为 1"],
        ["设备达标且非未成年", str(metrics["device_ok_non_minor_respondents"]), pct(metrics["device_ok_rate_over_non_minor"]), "分母为可确认非未成年"],
        ["最终通过", str(metrics["through_respondents"]), pct(metrics["through_rate_over_total"]), "展示口径：通过"],
    ]

    language_rows = []
    for lang, data in metrics["language_breakdown"].items():
        language_rows.append(
            [
                lang,
                str(data["total"]),
                pct(data["share_of_total"]),
                count_rate(data["minor"], data["total"]),
                count_rate(data["age_unknown"], data["total"]),
                str(data["non_minor"]),
                count_rate(data["device_ok_non_minor"], data["non_minor"]),
                count_rate(data["through"], data["total"]),
            ]
        )

    through = metrics["through_respondents"]
    user_type_rows = []
    for user_type in USER_TYPE_ORDER:
        count = metrics["through_user_type_counts"].get(user_type)
        if count:
            user_type_rows.append([user_type, str(count), pct(safe_rate(count, through))])
    for user_type, count in metrics["through_user_type_counts"].items():
        if user_type not in USER_TYPE_ORDER:
            user_type_rows.append([user_type, str(count), pct(safe_rate(count, through))])

    cumulative_rows = [
        [label, str(data["count"]), pct(data["rate"])]
        for label, data in metrics["through_user_type_cumulative"].items()
    ]

    lines = [
        "# 问卷筛选分析简报",
        "",
        f"> 数据源：`{source}`",
        f"> 生成时间：{metrics['generated_at']}",
        "",
        "## 一页结论",
        "",
        *[f"- {line}" for line in insight_lines(metrics)],
        "",
        "## 核心指标看板",
        "",
        "| 指标 | 数值 | 说明 |",
        "| --- | ---: | --- |",
        f"| 总样本 | {metrics['total_respondents']} | 处理后的问卷样本数 |",
        f"| 未成年率 | {pct(metrics['minor_rate'])} | {metrics['minor_respondents']}/{metrics['total_respondents']} |",
        f"| 设备达标率 | {pct(metrics['device_ok_rate_over_non_minor'])} | 设备达标且非未成年 / 非未成年 = {metrics['device_ok_non_minor_respondents']}/{metrics['non_minor_respondents']} |",
        f"| 通过人数 | {metrics['through_respondents']} | 占总样本 {pct(metrics['through_rate_over_total'])} |",
        f"| T0 率 | {pct(metrics['through_user_type_cumulative']['T0']['rate'])} | 通过人群内 T0 占比 |",
        f"| T0+T1 率 | {pct(metrics['through_user_type_cumulative']['T0+T1']['rate'])} | 通过人群内 T0/T1 合计占比 |",
        "",
        "## 筛选漏斗",
        "",
        *md_table(["阶段", "人数", "比例", "口径"], funnel_rows),
        "",
        "## 分语言表现",
        "",
        *md_table(["语言", "样本", "样本占比", "未成年", "年龄未知", "非未成年", "设备达标且非未成年", "通过"], language_rows),
        "",
        "## 通过人群 User Type 结构",
        "",
        "以下比例均以“通过人数”为分母。",
        "",
    ]

    if through:
        lines.extend(md_table(["User Type", "人数", "占通过人群比例"], user_type_rows))
        lines.extend(["", "### 累计高优先级比例", ""])
        lines.extend(md_table(["分组", "人数", "占通过人群比例"], cumulative_rows))
    else:
        lines.append("- 当前没有通过样本。")

    lines.extend(
        [
            "",
            "## 分析解读",
            "",
            f"1. 当前最大损耗来自年龄口径：总样本中未成年 {metrics['minor_respondents']} 人、年龄未知 {metrics['age_unknown_respondents']} 人，合计占 {pct(safe_rate(metrics['minor_respondents'] + metrics['age_unknown_respondents'], metrics['total_respondents']))}。这意味着多数样本在进入设备和用户类型判断前已经无法形成有效通过。",
            f"2. 在可确认非未成年样本中，设备达标率为 {pct(metrics['device_ok_rate_over_non_minor'])}，不是当前主要瓶颈。后续更值得优先排查的是年龄字段缺失和 Android 未命中机型。",
            f"3. 通过人群的高优先级浓度一般：T0+T1 为 {pct(metrics['through_user_type_cumulative']['T0+T1']['rate'])}，T0-T3 合计为 {pct(metrics['through_user_type_cumulative']['T0+T1+T2+T3']['rate'])}，说明通过样本中仍有较多 others。",
            "4. 分语言看，当前通过样本集中在 en；cht、jp、kr 的年龄分组为空，暂时不适合直接比较各地区通过率。",
            "",
            "## 建议动作",
            "",
            "- 优先确认 cht、jp、kr 的 q1 年龄题是否正常导出，避免这些语言被系统性排除在通过统计外。",
            "- 复核 Android 未命中机型明细，判断是否需要补充 V9 映射或设备别名。",
            "- 样本量扩大后，建议按语言分别观察通过率、T0 率、T0+T1 率，避免 en 样本占比过高掩盖地区差异。",
        ]
    )

    return "\n".join(lines) + "\n"


def html_table(headers: List[str], rows: List[List[str]]) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_html(metrics: Dict, source: Path) -> str:
    funnel_rows = [
        ["总样本", str(metrics["total_respondents"]), "100.0%", "处理后 CSV 全部行"],
        ["未成年", str(metrics["minor_respondents"]), pct(metrics["minor_rate"]), "age_group = 1"],
        ["年龄未知", str(metrics["age_unknown_respondents"]), pct(metrics["age_unknown_rate"]), "age_group 为空"],
        ["可确认非未成年", str(metrics["non_minor_respondents"]), pct(safe_rate(metrics["non_minor_respondents"], metrics["total_respondents"])), "age_group 非空且不为 1"],
        ["设备达标且非未成年", str(metrics["device_ok_non_minor_respondents"]), pct(metrics["device_ok_rate_over_non_minor"]), "分母为可确认非未成年"],
        ["最终通过", str(metrics["through_respondents"]), pct(metrics["through_rate_over_total"]), "展示口径：通过"],
    ]
    language_rows = [
        [
            lang,
            str(data["total"]),
            pct(data["share_of_total"]),
            count_rate(data["minor"], data["total"]),
            count_rate(data["age_unknown"], data["total"]),
            str(data["non_minor"]),
            count_rate(data["device_ok_non_minor"], data["non_minor"]),
            count_rate(data["through"], data["total"]),
        ]
        for lang, data in metrics["language_breakdown"].items()
    ]
    through = metrics["through_respondents"]
    user_type_rows = [
        [key, str(count), pct(safe_rate(count, through))]
        for key, count in metrics["through_user_type_counts"].items()
    ]
    cumulative_rows = [
        [label, str(data["count"]), pct(data["rate"])]
        for label, data in metrics["through_user_type_cumulative"].items()
    ]
    cards = [
        ("总样本", str(metrics["total_respondents"]), "处理后问卷样本"),
        ("未成年率", pct(metrics["minor_rate"]), f"{metrics['minor_respondents']}/{metrics['total_respondents']}"),
        ("设备达标率", pct(metrics["device_ok_rate_over_non_minor"]), f"{metrics['device_ok_non_minor_respondents']}/{metrics['non_minor_respondents']} 非未成年"),
        ("通过人数", str(metrics["through_respondents"]), pct(metrics["through_rate_over_total"])),
        ("T0 率", pct(metrics["through_user_type_cumulative"]["T0"]["rate"]), "通过人群内"),
        ("T0+T1 率", pct(metrics["through_user_type_cumulative"]["T0+T1"]["rate"]), "通过人群内"),
    ]
    card_html = "".join(
        f"<section class='card'><div class='label'>{html.escape(label)}</div><div class='value'>{html.escape(value)}</div><div class='note'>{html.escape(note)}</div></section>"
        for label, value, note in cards
    )
    insights = "".join(f"<li>{html.escape(line)}</li>" for line in insight_lines(metrics))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>问卷筛选分析简报</title>
  <style>
    body {{ margin: 0; background: #f6f7f9; color: #20242a; font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 36px 28px 56px; }}
    header {{ border-bottom: 3px solid #2f6f73; padding-bottom: 18px; margin-bottom: 24px; }}
    h1 {{ margin: 0 0 10px; font-size: 32px; line-height: 1.2; }}
    h2 {{ margin: 34px 0 14px; font-size: 22px; color: #20484b; }}
    .meta {{ color: #68717b; font-size: 13px; line-height: 1.7; }}
    .cards {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin: 22px 0 8px; }}
    .card {{ background: #fff; border: 1px solid #dde3e7; border-left: 5px solid #2f6f73; padding: 16px 18px; }}
    .label {{ color: #68717b; font-size: 13px; }}
    .value {{ font-size: 30px; font-weight: 700; margin-top: 6px; }}
    .note {{ color: #68717b; font-size: 12px; margin-top: 4px; }}
    .panel {{ background: #fff; border: 1px solid #dde3e7; padding: 18px 20px; }}
    li {{ margin: 8px 0; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #dde3e7; }}
    th {{ background: #eaf1f1; color: #244d50; text-align: left; font-weight: 700; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e4e8eb; font-size: 14px; }}
    td:not(:first-child), th:not(:first-child) {{ text-align: right; }}
    .two-col {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }}
    @media (max-width: 800px) {{ .cards, .two-col {{ grid-template-columns: 1fr; }} main {{ padding: 24px 16px; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>问卷筛选分析简报</h1>
    <div class="meta">数据源：{html.escape(str(source))}<br>生成时间：{html.escape(metrics["generated_at"])}</div>
  </header>
  <div class="cards">{card_html}</div>
  <h2>一页结论</h2>
  <section class="panel"><ul>{insights}</ul></section>
  <h2>筛选漏斗</h2>
  {html_table(["阶段", "人数", "比例", "口径"], funnel_rows)}
  <h2>分语言表现</h2>
  {html_table(["语言", "样本", "样本占比", "未成年", "年龄未知", "非未成年", "设备达标且非未成年", "通过"], language_rows)}
  <div class="two-col">
    <section>
      <h2>通过人群 User Type</h2>
      {html_table(["User Type", "人数", "占通过人群比例"], user_type_rows)}
    </section>
    <section>
      <h2>累计高优先级比例</h2>
      {html_table(["分组", "人数", "占通过人群比例"], cumulative_rows)}
    </section>
  </div>
  <h2>分析解读</h2>
  <section class="panel">
    <ol>
      <li>当前最大损耗来自年龄口径：未成年与年龄未知样本合计占 {html.escape(pct(safe_rate(metrics["minor_respondents"] + metrics["age_unknown_respondents"], metrics["total_respondents"])))}。</li>
      <li>设备不是当前可确认非未成年样本的主要瓶颈，设备达标率为 {html.escape(pct(metrics["device_ok_rate_over_non_minor"]))}。</li>
      <li>通过人群的高优先级浓度一般，T0+T1 为 {html.escape(pct(metrics["through_user_type_cumulative"]["T0+T1"]["rate"]))}，T0-T3 合计为 {html.escape(pct(metrics["through_user_type_cumulative"]["T0+T1+T2+T3"]["rate"]))}。</li>
      <li>分语言看，当前通过样本集中在 en；cht、jp、kr 的年龄分组为空，暂时不适合直接比较各地区通过率。</li>
    </ol>
  </section>
</main>
</body>
</html>
"""


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    if not args.input.exists():
        raise SystemExit(f"Input CSV does not exist: {args.input}")

    rows = read_rows(args.input)
    metrics = compute_metrics(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = args.output_dir / "questionnaire_brief_metrics.json"
    brief_path = args.output_dir / "questionnaire_brief.md"
    html_path = args.output_dir / "questionnaire_brief.html"
    metrics["input_csv"] = str(args.input)
    metrics["brief_md"] = str(brief_path)
    metrics["brief_html"] = str(html_path)
    metrics["metrics_json"] = str(metrics_path)

    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    brief_path.write_text(render_markdown(metrics, args.input), encoding="utf-8-sig")
    html_path.write_text(render_html(metrics, args.input), encoding="utf-8")

    print(
        json.dumps(
            {"brief_md": str(brief_path), "brief_html": str(html_path), "metrics_json": str(metrics_path)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
