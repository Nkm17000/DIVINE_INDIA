#!/usr/bin/env python3
import os, sys, time, requests
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VIDEO=ROOT/"output/daily_reel.mp4"
CAPTION=(ROOT/"output/caption.txt").read_text(encoding="utf-8")
GRAPH=os.getenv("META_GRAPH_VERSION","v24.0")

def facebook():
    page=os.environ["FB_PAGE_ID"]; token=os.environ["FB_PAGE_ACCESS_TOKEN"]
    with VIDEO.open("rb") as f:
        r=requests.post(
            f"https://graph.facebook.com/{GRAPH}/{page}/videos",
            params={"access_token":token,"description":CAPTION},
            files={"source":("daily_reel.mp4",f,"video/mp4")},
            timeout=180
        )
    r.raise_for_status()
    print("Facebook:",r.json())

def instagram():
    uid=os.environ["IG_USER_ID"]; token=os.environ["IG_ACCESS_TOKEN"]
    # Instagram requires a publicly reachable video URL. The workflow can be
    # extended with your preferred hosting provider. We deliberately fail
    # clearly rather than pretending a local file can be uploaded to IG.
    url=os.getenv("INSTAGRAM_VIDEO_URL")
    if not url:
        raise RuntimeError(
            "Instagram requires INSTAGRAM_VIDEO_URL (public MP4 URL). "
            "Video generation/artifact is unaffected."
        )
    r=requests.post(
        f"https://graph.facebook.com/{GRAPH}/{uid}/media",
        data={"media_type":"REELS","video_url":url,"caption":CAPTION,"access_token":token},
        timeout=60
    )
    r.raise_for_status()
    creation_id=r.json()["id"]
    for _ in range(30):
        time.sleep(5)
        s=requests.get(
            f"https://graph.facebook.com/{GRAPH}/{creation_id}",
            params={"fields":"status_code","access_token":token},
            timeout=30
        ).json()
        if s.get("status_code")=="FINISHED":
            break
        if s.get("status_code")=="ERROR":
            raise RuntimeError(f"Instagram processing failed: {s}")
    p=requests.post(
        f"https://graph.facebook.com/{GRAPH}/{uid}/media_publish",
        data={"creation_id":creation_id,"access_token":token},
        timeout=60
    )
    p.raise_for_status()
    print("Instagram:",p.json())

if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("Usage: publish.py facebook|instagram")
    {"facebook":facebook,"instagram":instagram}[sys.argv[1]]()
