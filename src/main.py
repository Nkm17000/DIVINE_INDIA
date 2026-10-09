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
RECENT_LIMIT = 10


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


def choose_pair(folder_name: str, images: list[Path], rings: list[Path],
                state: dict) -> tuple[Path, Path, dict]:
    """Select image+ring from matching deity folders; avoid last 10 pairs per folder."""
    # Include folder-relative names in the identity, not only basenames.
    folder_state = state["folders"].setdefault(
        folder_name, {"history": [], "last_selection": None, "cycle": 0}
    )
    history = folder_state.setdefault("history", [])
    available_pairs = [(im, ring) for im in images for ring in rings]
    if not available_pairs:
        raise RuntimeError(f"No valid image/ringtone pairs found for folder '{folder_name}'.")

    recent = {
        (entry.get("image"), entry.get("ring"))
        for entry in history[-RECENT_LIMIT:]
        if isinstance(entry, dict)
    }
    candidates = [
        (im, ring) for im, ring in available_pairs
        if (im.relative_to(IMAGE_ROOT).as_posix(),
            ring.relative_to(RING_ROOT).as_posix()) not in recent
    ]

    # If there are 10 or fewer total pairs, a repeated pair may become mathematically
    # unavoidable after the recent-history window covers every possible combination.
    if not candidates:
        candidates = available_pairs
        folder_state["cycle"] = int(folder_state.get("cycle", 0)) + 1

    image, ring = random.choice(candidates)
    selection = {
        "folder": folder_name,
        "image": image.relative_to(ROOT).as_posix(),
        "ring": ring.relative_to(ROOT).as_posix(),
        "selected_utc": datetime.now(timezone.utc).isoformat(),
    }
    history.append({
        "image": image.relative_to(IMAGE_ROOT).as_posix(),
        "ring": ring.relative_to(RING_ROOT).as_posix(),
        "selected_utc": selection["selected_utc"],
    })
    folder_state["history"] = history[-200:]
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


def verify_video(path: Path) -> None:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_frames", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    streams = json.loads(probe.stdout).get("streams", [])
    if not streams:
        raise RuntimeError(f"ffprobe found no video stream in {path}")
    stream = streams[0]
    if int(stream.get("width", 0)) != 1080 or int(stream.get("height", 0)) != 1920:
        raise RuntimeError(f"Unexpected dimensions for {path}: {stream}")
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

        image, ring, selection = choose_pair(folder_name, images, rings, state)
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
        verify_video(output)

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

    # Backwards compatibility with the existing single-video publisher.
    # The per-folder videos remain separate; this copy is NOT used to select media.
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
