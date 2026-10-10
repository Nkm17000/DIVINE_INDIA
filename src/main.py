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


def _build_pair_order(
    eligible_images: list[Path],
    eligible_rings: list[Path],
    used_pairs: set[str],
    recent_image_keys: list[str],
    recent_ring_keys: list[str],
) -> list[dict[str, str]]:
    """Create a full pair cycle while spacing both images and ringtones.

    Cyclic round-robin schedules cover every image/ringtone combination exactly
    once. Candidate schedules are accepted only if neither media item repeats in
    the previous ten selections, including the boundary from the prior cycle.
    """
    image_keys = [p.relative_to(IMAGE_ROOT).as_posix() for p in eligible_images]
    ring_keys = [p.relative_to(RING_ROOT).as_posix() for p in eligible_rings]
    remaining_pairs = [
        {"image": image_key, "ring": ring_key}
        for image_key in image_keys for ring_key in ring_keys
        if f"{image_key}|||{ring_key}" not in used_pairs
    ]
    if not remaining_pairs:
        return []

    # Generate one candidate schedule at a time to keep memory usage bounded
    # even when a deity has many images and ringtones.
    def schedule_candidates():
        # Cyclic schedules cover the Cartesian product exactly once. Different
        # phase offsets allow the next cycle to avoid the previous cycle's last ten.
        for phase in range(len(image_keys)):
            cyclic: list[dict[str, str]] = []
            for round_index in range(len(image_keys)):
                for ring_index, ring_key in enumerate(ring_keys):
                    cyclic.append({
                        "image": image_keys[(round_index + ring_index + phase) % len(image_keys)],
                        "ring": ring_key,
                    })
            yield cyclic
        for phase in range(len(ring_keys)):
            transposed: list[dict[str, str]] = []
            for round_index in range(len(ring_keys)):
                for image_index, image_key in enumerate(image_keys):
                    transposed.append({
                        "image": image_key,
                        "ring": ring_keys[(round_index + image_index + phase) % len(ring_keys)],
                    })
            yield transposed

    def valid_cycle(sequence: list[dict[str, str]]) -> bool:
        count = len(sequence)
        for i, pair in enumerate(sequence):
            for distance in range(1, min(RECENT_MEDIA_EXCLUSION, count - 1) + 1):
                previous = sequence[(i - distance) % count]
                if pair["image"] == previous["image"] or pair["ring"] == previous["ring"]:
                    return False
        return True

    recent_images = list(recent_image_keys[-RECENT_MEDIA_EXCLUSION:])
    recent_rings = list(recent_ring_keys[-RECENT_MEDIA_EXCLUSION:])
    for full in schedule_candidates():
        if not valid_cycle(full):
            continue
        # A media set can change mid-cycle; remove already-used pairs and check
        # the resulting schedule again before accepting it.
        remaining = [pair for pair in full
                     if f"{pair['image']}|||{pair['ring']}" not in used_pairs]
        if len(remaining) != len(remaining_pairs):
            continue
        if remaining and any(
            pair["image"] in recent_images or pair["ring"] in recent_rings
            for pair in remaining[:RECENT_MEDIA_EXCLUSION]
        ):
            # Try every rotation so the next run can start without repeating
            # any media from the last ten selections of the previous cycle.
            found = False
            for offset in range(1, len(remaining)):
                rotated = remaining[offset:] + remaining[:offset]
                if all(pair["image"] not in recent_images and pair["ring"] not in recent_rings
                       for pair in rotated[:RECENT_MEDIA_EXCLUSION]):
                    remaining = rotated
                    found = True
                    break
            if not found:
                continue
        return remaining

    raise RuntimeError(
        "Could not build a complete rotation satisfying both last-10 rules. "
        "Keep at least 20 distinct images and 20 distinct ringtones per deity, "
        "and avoid changing the media set mid-cycle."
    )


def choose_pair(folder_name: str, images: list[Path], rings: list[Path],
                state: dict) -> tuple[Path, Path, dict]:
    """Choose an unused image/ringtone pair; never reuse an image from the last 10."""
    folder_state = state["folders"].setdefault(
        folder_name, {
            "history": [], "used_pairs": [], "last_selection": None, "cycle": 0,
            "pair_order": [], "media_signature": None,
        }
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
    # A strict rule spanning the end/start of cycles needs 20 unique items:
    # the previous ten selections and the next ten must be able to use disjoint media.
    minimum_pool = 2 * RECENT_MEDIA_EXCLUSION
    if len(eligible_images) < minimum_pool:
        raise RuntimeError(
            f"Folder '{folder_name}' has {len(eligible_images)} images. At least "
            f"{minimum_pool} distinct images are required to guarantee no image repeats "
            f"within the last {RECENT_MEDIA_EXCLUSION} videos, including cycle resets."
        )
    if len(eligible_rings) < minimum_pool:
        raise RuntimeError(
            f"Folder '{folder_name}' has {len(eligible_rings)} ringtones. At least "
            f"{minimum_pool} distinct ringtones are required to guarantee no ringtone repeats "
            f"within the last {RECENT_MEDIA_EXCLUSION} videos, including cycle resets."
        )

    image_keys = [p.relative_to(IMAGE_ROOT).as_posix() for p in eligible_images]
    ring_keys = [p.relative_to(RING_ROOT).as_posix() for p in eligible_rings]
    valid_pair_keys = {
        f"{image_key}|||{ring_key}" for image_key in image_keys for ring_key in ring_keys
    }
    # Keep only ledger entries that still correspond to files in this media set.
    folder_state["used_pairs"] = list(dict.fromkeys(
        key for key in folder_state["used_pairs"] if key in valid_pair_keys
    ))
    total_pairs = len(valid_pair_keys)
    if len(folder_state["used_pairs"]) >= total_pairs:
        folder_state["cycle"] = int(folder_state.get("cycle", 0)) + 1
        folder_state["used_pairs"] = []
        folder_state["pair_order"] = []
        print(f"PAIR CYCLE RESET [{folder_name}]: all {total_pairs} combinations completed.")

    # Migrate old history into the ledger once only. Re-importing history on
    # every run would incorrectly mark pairs from earlier completed cycles as used.
    if not folder_state.get("history_migrated", False):
        for old_entry in folder_state["history"]:
            if isinstance(old_entry, dict) and old_entry.get("image") and old_entry.get("ring"):
                key = f"{old_entry['image']}|||{old_entry['ring']}"
                if key in valid_pair_keys and key not in folder_state["used_pairs"]:
                    folder_state["used_pairs"].append(key)
        folder_state["history_migrated"] = True

    # Re-check completion after one-time legacy migration.
    if len(folder_state["used_pairs"]) >= total_pairs:
        folder_state["cycle"] = int(folder_state.get("cycle", 0)) + 1
        folder_state["used_pairs"] = []
        folder_state["pair_order"] = []

    signature = json.dumps({"images": image_keys, "rings": ring_keys}, separators=(",", ":"))
    if folder_state.get("media_signature") != signature:
        # If files were added/removed, rebuild only the remaining part of the cycle.
        folder_state["pair_order"] = []
        folder_state["media_signature"] = signature

    recent_history = [
        item for item in folder_state["history"][-RECENT_MEDIA_EXCLUSION:]
        if isinstance(item, dict)
    ]
    recent_images = [item.get("image") for item in recent_history if item.get("image")]
    recent_rings = [item.get("ring") for item in recent_history if item.get("ring")]
    used_pairs = set(folder_state["used_pairs"])
    pair_order = folder_state.get("pair_order", [])
    remaining_valid = {
        f"{entry.get('image')}|||{entry.get('ring')}"
        for entry in pair_order if isinstance(entry, dict)
    }
    expected_remaining = valid_pair_keys - used_pairs
    if not pair_order or remaining_valid != expected_remaining:
        pair_order = _build_pair_order(
            eligible_images, eligible_rings, used_pairs, recent_images, recent_rings
        )
        folder_state["pair_order"] = pair_order

    if not pair_order:
        raise RuntimeError(
            f"Folder '{folder_name}' has no unused image/ringtone combinations available."
        )

    next_pair = pair_order.pop(0)
    image_key, ring_key = next_pair["image"], next_pair["ring"]
    image = IMAGE_ROOT / image_key
    ring = RING_ROOT / ring_key
    pair_key = f"{image_key}|||{ring_key}"
    if pair_key in used_pairs:
        raise RuntimeError(f"Rotation schedule attempted to reuse a pair in cycle {folder_state['cycle']}: {pair_key}")
    # Final guard: if this image somehow appears in recent history, refuse selection.
    if image_key in set(recent_images):
        raise RuntimeError(f"Rotation schedule attempted to repeat a recent image: {image_key}")
    if ring_key in set(recent_rings):
        raise RuntimeError(f"Rotation schedule attempted to repeat a recent ringtone: {ring_key}")

    selection = {
        "folder": folder_name,
        "image": image.relative_to(ROOT).as_posix(),
        "ring": ring.relative_to(ROOT).as_posix(),
        "selected_utc": datetime.now(timezone.utc).isoformat(),
        "cycle": folder_state["cycle"],
    }
    folder_state["used_pairs"].append(pair_key)
    folder_state["history"].append({
        "image": image_key,
        "ring": ring_key,
        "selected_utc": selection["selected_utc"],
    })
    folder_state["history"] = folder_state["history"][-5000:]
    folder_state["last_selection"] = selection
    return image, ring, selection


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

    # The folder names must match exactly (case-sensitive on GitHub's Linux runner).
    image_folders = {p.name: p for p in IMAGE_ROOT.iterdir() if p.is_dir()}
    ring_folders = {p.name: p for p in RING_ROOT.iterdir() if p.is_dir()}
    matched = sorted(set(image_folders) & set(ring_folders))
    unmatched_images = sorted(set(image_folders) - set(ring_folders))
    unmatched_rings = sorted(set(ring_folders) - set(image_folders))
    if unmatched_images:
        print("WARNING: no same-named ringtone folder; skipping image folder(s):",
              ", ".join(unmatched_images))
    if unmatched_rings:
        print("WARNING: no same-named image folder; skipping ringtone folder(s):",
              ", ".join(unmatched_rings))
    if not matched:
        raise RuntimeError("No exact folder-name matches between images/ and rings/.")

    state = load_state()
    generated = []
    for folder_name in matched:
        # CRITICAL SAFETY CHECK: only read files under the same named folder.
        images = media_in(image_folders[folder_name], IMAGE_EXTS)
        rings = media_in(ring_folders[folder_name], AUDIO_EXTS)
        if not images or not rings:
            print(f"SKIP {folder_name}: {len(images)} images, {len(rings)} ringtones.")
            continue

        try:
            image, ring, selection = choose_pair(folder_name, images, rings, state)
        except RuntimeError as exc:
            print(f"SKIP {folder_name}: {exc}")
            continue
        # Defence in depth: never render if the actual selected paths do not match.
        actual_folder = assert_same_deity_folder(image, ring)
        if actual_folder != folder_name:
            raise RuntimeError(
                f"MEDIA MISMATCH BLOCKED: expected '{folder_name}', selected '{actual_folder}'."
            )
        out_dir = OUT_ROOT / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / "daily_reel.mp4"
        seed_text = f"{selection['folder']}|{selection['image']}|{selection['ring']}|{selection['selected_utc']}"
        seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:8], 16)
        effects = create_video(image, ring, output, seed)
        verify_video(output, int(effects["width"]), int(effects["height"]))

        caption = {
            "hanumanji": "🙏 जय बजरंगबली 🙏",
            "maadurga": "🌺 जय माता दी 🌺",
            "shreekrishna": "🦚 जय श्री कृष्ण 🦚",
            "shyambaba": "🌸 जय श्री श्याम 🌸",
        }.get(folder_name.lower(), "🙏 जय श्री हरि 🙏")
        caption += "\n\n#Bhakti #Devotional #SanatanDharma"
        (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
        selection_out = {**selection, "video": output.relative_to(ROOT).as_posix(),
                         "effects": effects}
        (out_dir / "selection.json").write_text(
            json.dumps(selection_out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        generated.append((folder_name, output, caption, selection_out))
        print(f"GENERATED [{folder_name}]")
        print(f"  IMAGE: {image.relative_to(ROOT)}")
        print(f"  RING:  {ring.relative_to(ROOT)}")
        print(f"  VIDEO: {output.relative_to(ROOT)}")

    if not generated:
        raise RuntimeError("No videos generated: all matching folders were empty or invalid.")

    # Retain legacy aliases for integrations, while publishing uses folder-specific files.
    primary = generated[0]
    shutil.copy2(primary[1], OUT_ROOT / "daily_reel.mp4")
    (OUT_ROOT / "caption.txt").write_text(primary[2], encoding="utf-8")
    (OUT_ROOT / "selection.json").write_text(
        json.dumps(primary[3], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    save_state(state)
    print(f"SUCCESS: generated {len(generated)} folder-specific video(s): "
          + ", ".join(name for name, *_ in generated))


if __name__ == "__main__":
    main()
