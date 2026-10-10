#!/usr/bin/env python3
"""Merge generated image/ringtone selections and per-account publishing outcomes into CSV history."""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
RESULTS = ROOT / "publish_results"
HISTORY = ROOT / "data" / "history" / "publication_history.csv"
FIELDS = [
    "run_id", "recorded_at_utc", "selected_at_utc", "folder", "video",
    "image", "ringtone", "platform", "account_key", "account_id",
    "status", "post_id", "published_at_utc", "error",
]


def read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        print(f"WARNING: cannot read JSON history input: {path}")
        return None


def main() -> None:
    run_id = os.getenv("GITHUB_RUN_ID", "local")
    now = datetime.now(timezone.utc).isoformat()
    selections: dict[tuple[str, str], dict] = {}
    new_rows: list[dict] = []

    for path in sorted(OUTPUT.glob("*/selection*.json")):
        selection = read_json(path)
        if not selection:
            continue
        folder = str(selection.get("folder") or path.parent.name)
        video_path = str(selection.get("video") or "")
        video = Path(video_path).name if video_path else ("daily_reel.mp4" if path.name == "selection.json" else "")
        if not video:
            # selection_2.json corresponds to daily_reel_2.mp4, etc.
            suffix = path.stem.removeprefix("selection")
            video = f"daily_reel{suffix}.mp4" if suffix else "daily_reel.mp4"
        key = (folder, video)
        selections[key] = selection
        new_rows.append({
            "run_id": run_id,
            "recorded_at_utc": now,
            "selected_at_utc": str(selection.get("selected_utc", "")),
            "folder": folder,
            "video": video,
            "image": str(selection.get("image", "")),
            "ringtone": str(selection.get("ring", selection.get("audio", ""))),
            "platform": "GENERATION",
            "account_key": "",
            "account_id": "",
            "status": "GENERATED",
            "post_id": "",
            "published_at_utc": "",
            "error": "",
        })

    if RESULTS.exists():
        result_files = sorted(RESULTS.rglob("*.json"))
    else:
        result_files = []
    for path in result_files:
        result = read_json(path)
        if not result:
            continue
        result_platform = str(result.get("platform", "")).lower()
        result_folder = str(result.get("folder", ""))
        result_video = str(result.get("video", ""))
        records = result.get("records", [])
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            folder = str(record.get("folder") or result_folder)
            video = str(record.get("video") or result_video)
            selection = selections.get((folder, video), {})
            platform = str(record.get("platform") or result_platform).upper()
            new_rows.append({
                "run_id": str(result.get("run_id") or run_id),
                "recorded_at_utc": now,
                "selected_at_utc": str(selection.get("selected_utc", "")),
                "folder": folder,
                "video": video,
                "image": str(selection.get("image", "")),
                "ringtone": str(selection.get("ring", selection.get("audio", ""))),
                "platform": platform,
                "account_key": str(record.get("account_key", "")),
                "account_id": str(record.get("account_id", "")),
                "status": str(record.get("status", "UNKNOWN")).upper(),
                "post_id": str(record.get("post_id", "")),
                "published_at_utc": str(record.get("published_at", "")),
                "error": str(record.get("error", "")).replace("\r", " ").replace("\n", " "),
            })

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if HISTORY.exists():
        try:
            with HISTORY.open("r", encoding="utf-8-sig", newline="") as handle:
                existing = list(csv.DictReader(handle))
        except (OSError, csv.Error) as exc:
            raise RuntimeError(f"Could not read existing publication history CSV: {exc}") from exc

    # Idempotency: rerunning the history step must not duplicate rows for the same run/destination.
    def row_key(row: dict) -> tuple[str, ...]:
        return tuple(str(row.get(k, "")) for k in ("run_id", "platform", "folder", "video", "account_key", "status"))

    seen = {row_key(row) for row in existing}
    added = 0
    for row in new_rows:
        normalized = {field: str(row.get(field, "")) for field in FIELDS}
        key = row_key(normalized)
        if key in seen:
            continue
        existing.append(normalized)
        seen.add(key)
        added += 1

    with HISTORY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in FIELDS} for row in existing)
    print(f"Updated {HISTORY.relative_to(ROOT)}; added {added} rows. Media selections: {len(selections)}.")


if __name__ == "__main__":
    main()
