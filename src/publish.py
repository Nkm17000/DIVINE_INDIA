#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "output" / "daily_reel.mp4"
CAPTION_FILE = ROOT / "output" / "caption.txt"
GRAPH = os.getenv("META_GRAPH_VERSION", "v24.0")

def facebook():
    page = os.getenv("FB_PAGE_ID", "").strip()
    token = os.getenv("FB_PAGE_ACCESS_TOKEN", "").strip()

    if not page or not token:
        print("Facebook skipped: FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN is missing.")
        return

    with VIDEO.open("rb") as f:
        r = requests.post(
            f"https://graph.facebook.com/{GRAPH}/{page}/videos",
            params={
                "access_token": token,
                "description": CAPTION_FILE.read_text(encoding="utf-8"),
            },
            files={"source": ("daily_reel.mp4", f, "video/mp4")},
            timeout=300,
        )

    if not r.ok:
        raise RuntimeError(f"Facebook publish failed: HTTP {r.status_code}: {r.text}")

    print("Facebook published:", r.json())

def instagram():
    user_id = os.getenv("IG_USER_ID", "").strip()
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    video_url = os.getenv("INSTAGRAM_VIDEO_URL", "").strip()

    if not user_id or not token:
        print("Instagram skipped: IG_USER_ID or IG_ACCESS_TOKEN is missing.")
        return

    if not video_url:
        raise RuntimeError(
            "Instagram video URL was not created automatically. "
            "The workflow must create the public GitHub Release asset first."
        )

    caption = CAPTION_FILE.read_text(encoding="utf-8")

    print("Creating Instagram Reel container...")
    r = requests.post(
        f"https://graph.facebook.com/{GRAPH}/{user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": token,
        },
        timeout=120,
    )

    if not r.ok:
        raise RuntimeError(
            f"Instagram container creation failed: HTTP {r.status_code}: {r.text}"
        )

    creation_id = r.json().get("id")
    if not creation_id:
        raise RuntimeError(f"Instagram did not return a creation ID: {r.text}")

    print("Waiting for Instagram to finish processing...")
    for attempt in range(36):
        time.sleep(5)

        s = requests.get(
            f"https://graph.facebook.com/{GRAPH}/{creation_id}",
            params={
                "fields": "status_code,status",
                "access_token": token,
            },
            timeout=60,
        )

        if not s.ok:
            raise RuntimeError(
                f"Instagram status check failed: HTTP {s.status_code}: {s.text}"
            )

        data = s.json()
        status = data.get("status_code")

        print(f"Instagram processing attempt {attempt + 1}/36: {status}")

        if status == "FINISHED":
            break

        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram processing failed: {data}")
    else:
        raise RuntimeError("Instagram video processing timed out.")

    print("Publishing Instagram Reel...")
    p = requests.post(
        f"https://graph.facebook.com/{GRAPH}/{user_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": token,
        },
        timeout=120,
    )

    if not p.ok:
        raise RuntimeError(
            f"Instagram publish failed: HTTP {p.status_code}: {p.text}"
        )

    print("Instagram published:", p.json())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python src/publish.py facebook|instagram")

    action = sys.argv[1].lower()
    if action == "facebook":
        facebook()
    elif action == "instagram":
        instagram()
    else:
        raise SystemExit("Usage: python src/publish.py facebook|instagram")
