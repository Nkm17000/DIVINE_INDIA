#!/usr/bin/env python3
"""Generate one reel per deity folder, pairing media ONLY within that same folder."""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from video import create_video

ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = ROOT / "images"
RING_ROOT = ROOT / "rings"
OUT_ROOT = ROOT / "output"
STATE_FILE = ROOT / "state" / "rotation_state.json"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}
RECENT_MEDIA_EXCLUSION = 10


def media_in(folder: Path, extensions: set[str]) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*")
                  if p.is_file() and p.suffix.lower() in extensions)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                value.setdefault("folders", {})
                return value
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARNING: rotation state unreadable; starting a new state: {exc}")
    return {"schema_version": 2, "folders": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def eligible_media(files: list[Path], edge_count: int = 0) -> list[Path]:
    """Return all supported files; exclude recent selections by history, not filename order.

    The old first/last ten-file slicing left only two Hanuman images in a
    22-image folder, which caused the same image to recur with different tones.
    """
    return sorted(files, key=lambda p: p.as_posix().casefold())


def choose_pair(folder_name: str, images: list[Path], rings: list[Path],
                state: dict) -> tuple[Path, Path, dict]:
    """Choose an unused pair, relaxing recent-media exclusions 10 -> 7 -> 3 -> 1 -> 0.

    A pair is not reused within a cycle until all available image/ringtone pairs have
    been used. If a strict recent-media exclusion is impossible, progressively relax
    it instead of skipping the deity. The final 0 fallback guarantees a selection
    whenever at least one supported image and ringtone exist.
    """
    folder_state = state["folders"].setdefault(
        folder_name, {"history": [], "used_pairs": [], "last_selection": None, "cycle": 0,
                      "pair_order": [], "media_signature": None}
    )
    folder_state.setdefault("history", [])
    folder_state.setdefault("used_pairs", [])
    folder_state.setdefault("cycle", 0)

    eligible_images = eligible_media(images)
    eligible_rings = eligible_media(rings)
    if not eligible_images or not eligible_rings:
        raise RuntimeError(
            f"Folder '{folder_name}' has no usable images or ringtones. "
            f"Found {len(images)} images and {len(rings)} ringtones."
        )

    image_keys = [p.relative_to(IMAGE_ROOT).as_posix() for p in eligible_images]
    ring_keys = [p.relative_to(RING_ROOT).as_posix() for p in eligible_rings]
    valid_pairs = {f"{im}|||{ring}" for im in image_keys for ring in ring_keys}
    folder_state["used_pairs"] = list(dict.fromkeys(
        key for key in folder_state.get("used_pairs", []) if key in valid_pairs
    ))

    # Migrate previous history once, preserving the used-pair ledger where possible.
    if not folder_state.get("history_migrated", False):
        for entry in folder_state["history"]:
            if isinstance(entry, dict) and entry.get("image") and entry.get("ring"):
                key = f"{entry['image']}|||{entry['ring']}"
                if key in valid_pairs and key not in folder_state["used_pairs"]:
                    folder_state["used_pairs"].append(key)
        folder_state["history_migrated"] = True

    used = set(folder_state["used_pairs"])
    if len(used) >= len(valid_pairs):
        folder_state["cycle"] = int(folder_state.get("cycle", 0)) + 1
        folder_state["used_pairs"] = []
        used = set()
        print(f"PAIR CYCLE RESET [{folder_name}]: all {len(valid_pairs)} combinations completed.")

    recent_history = [entry for entry in folder_state["history"] if isinstance(entry, dict)]
    recent_images = [entry.get("image") for entry in recent_history if entry.get("image")]
    recent_rings = [entry.get("ring") for entry in recent_history if entry.get("ring")]
    remaining = [
        (im, ring) for im in image_keys for ring in ring_keys
        if f"{im}|||{ring}" not in used
    ]
    random.shuffle(remaining)

    chosen = None
    for window in (10, 7, 3, 1, 0):
        image_block = set(recent_images[-window:]) if window else set()
        ring_block = set(recent_rings[-window:]) if window else set()
        candidates = [(im, ring) for im, ring in remaining
                      if im not in image_block and ring not in ring_block]
        if candidates:
            chosen = random.choice(candidates)
            if window < 10:
                print(f"ROTATION FALLBACK [{folder_name}]: using last-{window} exclusion "
                      f"(last-10 could not be satisfied)." if window else
                      f"ROTATION FALLBACK [{folder_name}]: no recent-media exclusion was possible; "
                      "using an available combination.")
            break

    # This should only be reachable if the media lists changed unexpectedly mid-run.
    if chosen is None:
        raise RuntimeError(f"Folder '{folder_name}' has no available image/ringtone pair.")

    image_key, ring_key = chosen
    image, ring = IMAGE_ROOT / image_key, RING_ROOT / ring_key
    pair_key = f"{image_key}|||{ring_key}"
    selected_utc = datetime.now(timezone.utc).isoformat()
    selection = {
        "folder": folder_name, "image": image.relative_to(ROOT).as_posix(),
        "ring": ring.relative_to(ROOT).as_posix(), "selected_utc": selected_utc,
        "cycle": folder_state["cycle"],
    }
    folder_state["used_pairs"].append(pair_key)
    folder_state["history"].append({"image": image_key, "ring": ring_key,
                                   "selected_utc": selected_utc})
    folder_state["history"] = folder_state["history"][-5000:]
    folder_state["last_selection"] = selection
    return image, ring, selection


def load_video_counts() -> dict[str, int]:
    """Read per-deity video counts from the existing social_accounts.json config.

    Each account's folders may use legacy strings or objects like
    {"name": "hanumanji", "count": 2}. Counts repeated under Facebook and
    Instagram must agree; unspecified counts default to one.
    """
    config_path = ROOT / "config" / "social_accounts.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing account config: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("config/social_accounts.json must be a JSON object.")

    counts: dict[str, int] = {}
    for platform in ("facebook", "instagram"):
        mappings = data.get(platform, {})
        if not isinstance(mappings, dict):
            raise RuntimeError(f"config/social_accounts.json: '{platform}' must be an object.")
        for account_key, account_config in mappings.items():
            if isinstance(account_config, list):
                folder_entries = account_config
            elif isinstance(account_config, dict):
                folder_entries = account_config.get("folders", [])
            else:
                raise RuntimeError(f"{platform}.{account_key} must contain a folders array.")
            if not isinstance(folder_entries, list):
                raise RuntimeError(f"{platform}.{account_key}.folders must be an array.")
            for entry in folder_entries:
                if isinstance(entry, str):
                    name, count = entry.strip(), 1
                elif isinstance(entry, dict):
                    name = entry.get("name", "")
                    count = entry.get("count", 1)
                    if not isinstance(name, str):
                        raise RuntimeError(f"Invalid deity name in {platform}.{account_key}.folders: {entry!r}")
                    name = name.strip()
                    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                        raise RuntimeError(f"Invalid video count for '{name}': count must be a positive integer.")
                else:
                    raise RuntimeError(
                        f"Each folder must be a name string or an object with name/count; got {entry!r}."
                    )
                if not name:
                    raise RuntimeError(f"Empty deity name in {platform}.{account_key}.folders.")
                if name in counts and counts[name] != count:
                    raise RuntimeError(
                        f"Conflicting video counts for '{name}' in config/social_accounts.json: "
                        f"{counts[name]} versus {count}. Keep the count consistent across platforms/accounts."
                    )
                counts[name] = count
    return counts

def assert_same_deity_folder(image: Path, ring: Path) -> str:
    """Fail closed unless image and audio are under the same deity folder."""
    try:
        image_rel = image.resolve().relative_to(IMAGE_ROOT.resolve())
        ring_rel = ring.resolve().relative_to(RING_ROOT.resolve())
    except ValueError as exc:
        raise RuntimeError("Selected image/audio is outside its approved media root.") from exc
    if not image_rel.parts or not ring_rel.parts or image_rel.parts[0] != ring_rel.parts[0]:
        raise RuntimeError(
            f"MEDIA MISMATCH BLOCKED: image folder '{image_rel.parts[0] if image_rel.parts else '?'}' "
            f"does not match ringtone folder '{ring_rel.parts[0] if ring_rel.parts else '?'}'."
        )
    return image_rel.parts[0]


def verify_video(path: Path, expected_width: int, expected_height: int) -> None:
    """Verify the rendered video against the orientation selected by create_video()."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_frames", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(probe.stdout).get("streams", [])
    if not streams:
        raise RuntimeError(f"ffprobe found no video stream in {path}")
    stream = streams[0]
    actual_width = int(stream.get("width", 0))
    actual_height = int(stream.get("height", 0))
    if actual_width != expected_width or actual_height != expected_height:
        raise RuntimeError(
            f"Unexpected dimensions for {path}: got {actual_width}x{actual_height}; "
            f"expected {expected_width}x{expected_height}."
        )
    # Audio length determines the final video length, so short ringtone clips are valid.
    if int(stream.get("nb_frames", 0)) < 2:
        raise RuntimeError(f"Video has too few frames: {path}: {stream}")


def main() -> None:
    if not IMAGE_ROOT.is_dir() or not RING_ROOT.is_dir():
        raise RuntimeError(
            "Required folders missing. Expected images/<deity>/ and rings/<same-deity>/."
        )

    image_folders = {p.name: p for p in IMAGE_ROOT.iterdir() if p.is_dir()}
    ring_folders = {p.name: p for p in RING_ROOT.iterdir() if p.is_dir()}
    matched = sorted(set(image_folders) & set(ring_folders))
    unmatched_images = sorted(set(image_folders) - set(ring_folders))
    unmatched_rings = sorted(set(ring_folders) - set(image_folders))
    if unmatched_images:
        print("WARNING: no same-named ringtone folder; cannot generate:", ", ".join(unmatched_images))
    if unmatched_rings:
        print("WARNING: no same-named image folder; cannot generate:", ", ".join(unmatched_rings))
    if not matched:
        raise RuntimeError("No exact folder-name matches between images/ and rings/.")

    counts = load_video_counts()
    for configured_name in counts:
        if configured_name not in matched:
            print(f"WARNING: configured deity '{configured_name}' has no matching images/ and rings/ folders.")
    state = load_state()
    generated = []
    for folder_name in matched:
        images = media_in(image_folders[folder_name], IMAGE_EXTS)
        rings = media_in(ring_folders[folder_name], AUDIO_EXTS)
        if not images or not rings:
            print(f"SKIP {folder_name}: {len(images)} images, {len(rings)} ringtones; media is missing.")
            continue

        video_count = counts.get(folder_name, 1)
        out_dir = OUT_ROOT / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)
        caption = {
            "hanumanji": "🙏 जय बजरंगबली 🙏",
            "maadurga": "🌺 जय माता दी 🌺",
            "shreekrishna": "🦚 जय श्री कृष्ण 🦚",
            "shyambaba": "🌸 जय श्री श्याम 🌸",
        }.get(folder_name.lower(), "🙏 जय श्री हरि 🙏")
        caption += "\n\n#Bhakti #Devotional #SanatanDharma"
        (out_dir / "caption.txt").write_text(caption, encoding="utf-8")

        for video_index in range(1, video_count + 1):
            try:
                image, ring, selection = choose_pair(folder_name, images, rings, state)
                actual_folder = assert_same_deity_folder(image, ring)
                if actual_folder != folder_name:
                    raise RuntimeError(
                        f"MEDIA MISMATCH BLOCKED: expected '{folder_name}', selected '{actual_folder}'."
                    )
                filename = "daily_reel.mp4" if video_index == 1 else f"daily_reel_{video_index}.mp4"
                output = out_dir / filename
                seed_text = (f"{selection['folder']}|{selection['image']}|{selection['ring']}|"
                             f"{selection['selected_utc']}|{video_index}")
                seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:8], 16)
                effects = create_video(image, ring, output, seed)
                verify_video(output, int(effects["width"]), int(effects["height"]))
                selection_out = {**selection, "video": output.relative_to(ROOT).as_posix(),
                                 "video_index": video_index, "effects": effects}
                selection_name = "selection.json" if video_index == 1 else f"selection_{video_index}.json"
                (out_dir / selection_name).write_text(
                    json.dumps(selection_out, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                generated.append((folder_name, output, caption, selection_out))
                print(f"GENERATED [{folder_name}] video {video_index}/{video_count}")
                print(f"  IMAGE: {image.relative_to(ROOT)}")
                print(f"  RING:  {ring.relative_to(ROOT)}")
                print(f"  VIDEO: {output.relative_to(ROOT)}")
            except Exception as exc:
                # Continue with other requested videos/deities; rotation fallback itself
                # never rejects a valid folder just because last-10 cannot be satisfied.
                print(f"ERROR generating [{folder_name}] video {video_index}/{video_count}: {exc}")

    if not generated:
        raise RuntimeError("No videos generated: all matching folders were empty or video rendering failed.")

    primary = generated[0]
    shutil.copy2(primary[1], OUT_ROOT / "daily_reel.mp4")
    (OUT_ROOT / "caption.txt").write_text(primary[2], encoding="utf-8")
    (OUT_ROOT / "selection.json").write_text(
        json.dumps(primary[3], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_state(state)
    print(f"SUCCESS: generated {len(generated)} folder-specific video(s): "
          + ", ".join(f"{name}/{video.name}" for name, video, *_ in generated))


if __name__ == "__main__":
    main()
