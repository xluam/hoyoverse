#!/usr/bin/env python
"""Process multilingual questionnaire CSV exports into a standard schema."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


DEFAULT_INPUT_DIR = Path(r"C:\Users\xinyi.lu02\echoworkspace\downloads")
DEFAULT_OUTPUT_DIR = Path(r"C:\Users\xinyi.lu02\Desktop\ai-data-dashboard\outputs\questionnaire_processor")
DEFAULT_UA_SKILL_DIR = Path(r"C:\Users\xinyi.lu02\.codex\skills\ua-device-performance")

OUTPUT_COLUMNS = [
    "id",
    "lang",
    "user_agent",
    "ip_area",
    "age",
    "gender",
    "Android",
    "ios",
    "PC",
    "ios_model",
    "qc4",
    "phone_player",
    "PC_player",
    "console_player",
    "non-player",
    "pokemon_go",
    "pokemon_tcg_pocket",
    "monster_hunter_now",
    "afk_arena",
    "marvel_snap",
    "dragon_ball_z_dokkan_battle",
    "dragon_ball_legends",
    "love_and_deepspace",
    "genshin_impact",
    "honkai_star_rail",
    "zenless_zone_zero",
    "honkai_impact_3rd",
    "cookie_run_kingdom",
    "puzzle_and_dragons",
    "yokai_watch",
    "uma_musume",
    "pokemon_sword_shield",
    "pokemon_scarlet_violet",
    "pokemon_legends_za",
    "pokemon_pokopia",
    "animal_crossing",
    "naruto_clash_of_ninja_2",
    "wuthering_waves",
    "final_fantasy",
    "palworld",
    "email",
    "googleplay",
    "age_group",
    "device_ok",
    "user_type",
    "pass",
]

COMMON_Q_MAP = {
    "pokemon_go": "q6_1",
    "pokemon_tcg_pocket": "q6_2",
    "pokemon_sword_shield": "q7_1",
    "pokemon_scarlet_violet": "q7_2",
    "pokemon_legends_za": "q7_3",
    "pokemon_pokopia": "q7_4",
    "animal_crossing": "q7_5",
    "naruto_clash_of_ninja_2": "q7_6",
    "wuthering_waves": "q7_7",
    "final_fantasy": "q7_8",
    "palworld": "q7_9",
}

LANG_Q_MAP = {
    "en": {
        "monster_hunter_now": "q6_3",
        "afk_arena": "q6_4",
        "marvel_snap": "q6_5",
        "dragon_ball_z_dokkan_battle": "q6_6",
        "love_and_deepspace": "q6_7",
        "genshin_impact": "q6_8",
        "honkai_star_rail": "q6_9",
        "zenless_zone_zero": "q6_10",
        "honkai_impact_3rd": "q6_11",
    },
    "jp": {
        "monster_hunter_now": "q6_3",
        "puzzle_and_dragons": "q6_4",
        "yokai_watch": "q6_5",
        "love_and_deepspace": "q6_6",
        "genshin_impact": "q6_7",
        "honkai_star_rail": "q6_8",
        "zenless_zone_zero": "q6_9",
        "honkai_impact_3rd": "q6_10",
    },
    "kr": {
        "cookie_run_kingdom": "q6_3",
        "monster_hunter_now": "q6_4",
        "afk_arena": "q6_5",
        "love_and_deepspace": "q6_6",
        "genshin_impact": "q6_7",
        "honkai_star_rail": "q6_8",
        "zenless_zone_zero": "q6_9",
        "honkai_impact_3rd": "q6_10",
    },
    "cht": {
        "monster_hunter_now": "q6_3",
        "uma_musume": "q6_4",
        "afk_arena": "q6_5",
        "dragon_ball_legends": "q6_6",
        "love_and_deepspace": "q6_7",
        "genshin_impact": "q6_8",
        "honkai_star_rail": "q6_9",
        "zenless_zone_zero": "q6_10",
        "honkai_impact_3rd": "q6_11",
    },
}


def clean(value) -> str:
    return "" if value is None else str(value).strip()


def int_value(value) -> Optional[int]:
    text = clean(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text)
    if not match:
        return None
    return int(match.group(0))


def is_one(value) -> bool:
    return clean(value) == "1"


def read_csv(path: Path) -> Tuple[List[str], List[dict], str]:
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "cp950"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                return list(reader.fieldnames or []), rows, encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeDecodeError("csv", b"", 0, 1, f"Unable to decode {path}: {last_error}")


def column_by_prefix(fieldnames: Iterable[str], prefix: str) -> Optional[str]:
    if prefix in fieldnames:
        return prefix
    marker = prefix + "_"
    for name in fieldnames:
        if name == prefix or name.startswith(marker):
            return name
    return None


def getq(row: dict, fieldnames: List[str], prefix: str) -> str:
    column = column_by_prefix(fieldnames, prefix)
    return clean(row.get(column)) if column else ""


def valid_export(fieldnames: List[str]) -> bool:
    required = {"id", "user_agent", "ip_area", "q1", "q2", "q4", "qc4"}
    present = set(fieldnames)
    has_prefixed = all(any(name == q or name.startswith(q + "_") for name in fieldnames) for q in ("q3_1", "q3_2", "q3_3"))
    return required.issubset(present) and has_prefixed


def skip_row(row: dict) -> bool:
    row_id = clean(row.get("id"))
    if not row_id:
        return True
    return bool(re.fullmatch(r"L\d+", row_id, flags=re.I))


def compute_age(q1_value: str) -> str:
    selected = int_value(q1_value)
    if selected is None:
        return ""
    if selected == 46:
        return "45+"
    return str(selected - 1)


def age_for_group(age_value: str) -> Optional[int]:
    if age_value == "45+":
        return 45
    return int_value(age_value)


def compute_age_group(lang: str, age_value: str) -> str:
    age = age_for_group(age_value)
    if age is None:
        return ""
    if lang == "kr":
        if age < 19:
            return "1"
        if 19 <= age <= 22:
            return "2"
    else:
        if age < 18:
            return "1"
        if 18 <= age <= 22:
            return "2"
    if 23 <= age <= 26:
        return "3"
    if 27 <= age <= 30:
        return "4"
    if 31 <= age <= 35:
        return "5"
    if age >= 36:
        return "6"
    return ""


def build_base_row(source: dict, fieldnames: List[str], lang: str) -> dict:
    age = compute_age(getq(source, fieldnames, "q1"))
    out = {column: "" for column in OUTPUT_COLUMNS}
    out.update(
        {
            "id": clean(source.get("id")),
            "lang": lang,
            "user_agent": clean(source.get("user_agent")),
            "_android_user_agent": clean(source.get("origin_user_agent")) or clean(source.get("user_agent")),
            "ip_area": clean(source.get("ip_area")),
            "age": age,
            "gender": getq(source, fieldnames, "q2"),
            "Android": getq(source, fieldnames, "q3_1"),
            "ios": getq(source, fieldnames, "q3_2"),
            "PC": getq(source, fieldnames, "q3_3"),
            "ios_model": getq(source, fieldnames, "q4"),
            "qc4": clean(source.get("qc4")),
            "phone_player": getq(source, fieldnames, "q5_1"),
            "PC_player": getq(source, fieldnames, "q5_2"),
            "console_player": getq(source, fieldnames, "q5_3"),
            "non-player": getq(source, fieldnames, "q5_4"),
            "email": getq(source, fieldnames, "q8"),
            "googleplay": getq(source, fieldnames, "q9"),
            "age_group": compute_age_group(lang, age),
        }
    )

    q_map = dict(COMMON_Q_MAP)
    q_map.update(LANG_Q_MAP.get(lang, {}))
    for output_col, q_col in q_map.items():
        out[output_col] = getq(source, fieldnames, q_col)
    return out


def find_default_rules(output_dir: Path) -> Optional[Path]:
    candidates = []
    for root in [
        output_dir,
        Path.cwd() / "outputs",
        Path(r"C:\Users\xinyi.lu02\Desktop\ai-data-dashboard\outputs"),
    ]:
        if root.exists():
            candidates.extend(root.rglob("matomo_mobiles.yml"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def run_android_judgment(
    rows: List[dict],
    output_dir: Path,
    ua_skill_dir: Path,
    v9: Optional[Path],
    matomo_rules: Optional[Path],
    strict: bool,
) -> Tuple[Dict[int, bool], dict]:
    android_indexes = [idx for idx, row in enumerate(rows) if is_one(row.get("Android"))]
    summary = {"android_rows": len(android_indexes), "called": False}
    if not android_indexes:
        return {}, summary

    ua_script = ua_skill_dir / "scripts" / "judge_ua_v9.py"
    if not ua_script.exists():
        message = f"ua-device-performance script not found: {ua_script}"
        if strict:
            raise FileNotFoundError(message)
        summary["warning"] = message
        return {}, summary

    ua_dir = output_dir / "_ua_device_performance"
    ua_dir.mkdir(parents=True, exist_ok=True)
    ua_input = ua_dir / "android_user_agents.csv"
    with ua_input.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["user_agent"])
        writer.writeheader()
        for idx in android_indexes:
            writer.writerow({"user_agent": rows[idx].get("_android_user_agent") or rows[idx].get("user_agent", "")})

    rules = matomo_rules or find_default_rules(output_dir)
    command = [
        sys.executable,
        str(ua_script),
        "--input",
        str(ua_input),
        "--output-dir",
        str(ua_dir),
    ]
    if v9:
        command.extend(["--v9", str(v9)])
    if rules:
        command.extend(["--rules", str(rules)])

    summary.update({"called": True, "input": str(ua_input), "output_dir": str(ua_dir), "rules": str(rules) if rules else ""})
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        summary["stdout"] = completed.stdout[-2000:]
        summary["stderr"] = completed.stderr[-2000:]
    except subprocess.CalledProcessError as exc:
        summary["error"] = (exc.stderr or exc.stdout or str(exc))[-4000:]
        if strict:
            raise
        return {}, summary

    matched_path = ua_dir / "ua_v9_device_performance_matched.csv"
    if not matched_path.exists():
        message = f"UA matched output not found: {matched_path}"
        if strict:
            raise FileNotFoundError(message)
        summary["warning"] = message
        return {}, summary

    with matched_path.open("r", encoding="utf-8-sig", newline="") as handle:
        matched_rows = list(csv.DictReader(handle))

    result: Dict[int, bool] = {}
    pass_values = {"是", "yes", "YES", "1", "true", "True"}
    pass_statuses = {"达标"}
    for idx, matched in zip(android_indexes, matched_rows):
        values = {clean(value) for value in matched.values()}
        result[idx] = bool(values & pass_values or values & pass_statuses)

    summary["matched_rows"] = len(matched_rows)
    summary["android_pass_rows"] = sum(1 for passed in result.values() if passed)
    return result, summary


def compute_device_flags(rows: List[dict], android_pass: Dict[int, bool]) -> None:
    ios_pass_models = {"1", "2", "4", "6"}
    for idx, row in enumerate(rows):
        android_selected = is_one(row.get("Android"))
        ios_selected = is_one(row.get("ios"))
        android_ok = android_selected and android_pass.get(idx, False)
        ios_ok = ios_selected and clean(row.get("ios_model")) in ios_pass_models
        row["device_ok"] = "1" if android_ok or ios_ok else "0"


def game_num(row: dict, column: str) -> Optional[int]:
    return int_value(row.get(column))


def classify_user_type(row: dict) -> str:
    target_games = ["pokemon_go", "pokemon_tcg_pocket"]
    if row.get("lang") == "kr":
        target_games.append("cookie_run_kingdom")
    target_values = [game_num(row, col) for col in target_games]
    has_target_4 = any(value == 4 for value in target_values)
    has_target_3 = any(value == 3 for value in target_values)

    mihoyo_games = ["genshin_impact", "honkai_star_rail", "zenless_zone_zero", "honkai_impact_3rd"]
    mihoyo_values = [game_num(row, col) for col in mihoyo_games]
    if any(value is None for value in mihoyo_values):
        return "others"

    all_mihoyo_1 = all(value == 1 for value in mihoyo_values)
    all_mihoyo_le2 = all(value <= 2 for value in mihoyo_values)

    if has_target_4 and all_mihoyo_1:
        return "T0"
    if has_target_3 and all_mihoyo_1:
        return "T1"
    if has_target_4 and all_mihoyo_le2:
        return "T2"
    if has_target_3 and all_mihoyo_le2:
        return "T3"
    return "others"


def finalize_rows(rows: List[dict]) -> None:
    for row in rows:
        row["user_type"] = classify_user_type(row)
        row["pass"] = "1" if row.get("device_ok") == "1" and row.get("age_group") != "1" and row.get("age_group") else "0"


def process_files(input_dir: Path) -> Tuple[List[dict], List[dict], List[str]]:
    output_rows: List[dict] = []
    file_summaries: List[dict] = []
    warnings: List[str] = []

    for path in sorted(input_dir.glob("*.csv")):
        lang = path.stem.lower()
        try:
            fieldnames, source_rows, encoding = read_csv(path)
        except Exception as exc:
            warnings.append(f"Skipped {path.name}: {exc}")
            file_summaries.append({"file": str(path), "lang": lang, "rows": 0, "status": "decode_error"})
            continue

        if not valid_export(fieldnames):
            warnings.append(f"Skipped {path.name}: not a standard survey export; missing expected questionnaire columns.")
            file_summaries.append(
                {"file": str(path), "lang": lang, "rows": len(source_rows), "status": "skipped_non_export", "encoding": encoding}
            )
            continue

        before = len(output_rows)
        for source in source_rows:
            if skip_row(source):
                continue
            output_rows.append(build_base_row(source, fieldnames, lang))

        file_summaries.append(
            {
                "file": str(path),
                "lang": lang,
                "source_rows": len(source_rows),
                "output_rows": len(output_rows) - before,
                "status": "processed",
                "encoding": encoding,
            }
        )

    return output_rows, file_summaries, warnings


def write_outputs(rows: List[dict], output_dir: Path, report: dict) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "questionnaire_processed.csv"
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in OUTPUT_COLUMNS})

    report_json = output_dir / "questionnaire_processing_report.json"
    report["output_csv"] = str(output_csv)
    report["report_json"] = str(report_json)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_csv, report_json


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--ua-skill-dir", type=Path, default=DEFAULT_UA_SKILL_DIR)
    parser.add_argument("--v9", type=Path)
    parser.add_argument("--matomo-rules", type=Path)
    parser.add_argument("--strict-device", action="store_true", help="Fail if Android device judgment cannot run.")
    args = parser.parse_args(argv)

    if not args.input_dir.exists():
        raise SystemExit(f"Input directory does not exist: {args.input_dir}")

    rows, file_summaries, warnings = process_files(args.input_dir)
    android_pass, android_summary = run_android_judgment(
        rows=rows,
        output_dir=args.output_dir,
        ua_skill_dir=args.ua_skill_dir,
        v9=args.v9,
        matomo_rules=args.matomo_rules,
        strict=args.strict_device,
    )
    if android_summary.get("warning"):
        warnings.append(android_summary["warning"])
    if android_summary.get("error"):
        warnings.append("Android device judgment failed; Android rows were treated as device_ok=0.")

    compute_device_flags(rows, android_pass)
    finalize_rows(rows)

    report = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(args.input_dir),
        "output_dir": str(args.output_dir),
        "columns": OUTPUT_COLUMNS,
        "column_count": len(OUTPUT_COLUMNS),
        "row_count": len(rows),
        "files": file_summaries,
        "warnings": warnings,
        "android_device_judgment": android_summary,
        "pass_count": sum(1 for row in rows if row.get("pass") == "1"),
        "device_ok_count": sum(1 for row in rows if row.get("device_ok") == "1"),
        "user_type_counts": {},
    }
    for row in rows:
        report["user_type_counts"][row["user_type"]] = report["user_type_counts"].get(row["user_type"], 0) + 1

    output_csv, report_json = write_outputs(rows, args.output_dir, report)
    print(json.dumps({"output_csv": str(output_csv), "report_json": str(report_json), "rows": len(rows)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
