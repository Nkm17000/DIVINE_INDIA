#!/usr/bin/env python3
from __future__ import annotations
import os, sys, time
from pathlib import Path

try:
    import requests
except ImportError as exc:
    raise SystemExit(
        "Python dependency 'requests' is missing. "
        "Run: python -m pip install -r requirements.txt"
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "output/daily_reel.mp4"
CAPTION_FILE = ROOT / "output/caption.txt"
GRAPH = os.getenv("META_GRAPH_VERSION") or "v24.0"


def caption() -> str:
    return CAPTION_FILE.read_text(encoding="utf-8") if CAPTION_FILE.exists() else "🙏 राधे राधे 🙏"


def facebook() -> None:
    page = os.getenv("FB_PAGE_ID", "").strip()
    token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page or not token:
        print("Facebook skipped: FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN is missing.")
        return
    if not VIDEO.exists():
        raise RuntimeError(f"Video not found: {VIDEO}")
    with VIDEO.open("rb") as f:
        r = requests.post(
            f"https://graph.facebook.com/{GRAPH}/{page}/videos",
            params={"access_token": token, "description": caption()},
            files={"source": ("daily_reel.mp4", f, "video/mp4")},
            timeout=300,
        )
    r.raise_for_status()
    print("Facebook published:", r.json())


def instagram() -> None:
    uid = os.getenv("IG_USER_ID", "").strip()
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    if not uid or not token:
        print("Instagram skipped: IG_USER_ID or IG_ACCESS_TOKEN is missing.")
        return
    url = os.getenv("INSTAGRAM_VIDEO_URL", "").strip()
    if not url:
        print("Instagram skipped: INSTAGRAM_VIDEO_URL is missing.")
        return

    r = requests.post(
        f"https://graph.facebook.com/{GRAPH}/{uid}/media",
        data={
            "media_type": "REELS",
            "video_url": url,
            "caption": caption(),
            "access_token": token,
        },
        timeout=90,
    )
    r.raise_for_status()
    creation_id = r.json()["id"]

    for _ in range(36):
        time.sleep(5)
        status = requests.get(
            f"https://graph.facebook.com/{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=60,
        )
        status.raise_for_status()
        code = status.json().get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram processing failed: {status.json()}")
    else:
        raise RuntimeError("Instagram reel processing timed out after 3 minutes.")

    published = requests.post(
        f"https://graph.facebook.com/{GRAPH}/{uid}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=90,
    )
    published.raise_for_status()
    print("Instagram published:", published.json())


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"facebook", "instagram"}:
        raise SystemExit("Usage: python src/publish.py facebook|instagram")
    if sys.argv[1] == "facebook":
        facebook()
    else:
        instagram()
