import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import *
from src.meta import post_facebook, post_instagram

ROOT = Path(__file__).resolve().parent
OUT = ROOT / OUTPUT_DIR
VIDEO = OUT / "daily_reel.mp4"
SELECTION = OUT / "selection.json"


def _facebook_ready():
    return bool(POST_TO_FACEBOOK and FB_PAGE_ID.strip() and FB_PAGE_ACCESS_TOKEN.strip())


def _instagram_ready():
    return bool(POST_TO_INSTAGRAM and IG_USER_ID.strip() and IG_ACCESS_TOKEN.strip())


def main():
    if not VIDEO.exists() or not SELECTION.exists():
        raise RuntimeError("Run main.py first.")
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    caption = selection["caption"]
    results = {}

    if _facebook_ready():
        print("Posting to Facebook...")
        try:
            results["facebook"] = post_facebook(str(VIDEO), caption)
            print("Facebook posted.")
        except Exception as exc:
            results["facebook"] = {"status": "failed", "error": str(exc)}
            print(f"Facebook publish failed: {exc}")
    else:
        results["facebook"] = {"status": "skipped", "reason": "FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN is missing"}
        print("Facebook skipped: FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN not configured.")

    if _instagram_ready():
        video_url = PUBLIC_VIDEO_URL
        if not video_url and GITHUB_REPOSITORY:
            video_url = f"https://github.com/{GITHUB_REPOSITORY}/releases/download/{GITHUB_RELEASE_TAG}/{GITHUB_RELEASE_ASSET}"
        if video_url:
            print("Instagram video URL:", video_url)
            try:
                results["instagram"] = post_instagram(video_url, caption)
                print("Instagram posted.")
            except Exception as exc:
                results["instagram"] = {"status": "failed", "error": str(exc)}
                print(f"Instagram publish failed: {exc}")
        else:
            results["instagram"] = {"status": "skipped", "reason": "No PUBLIC_VIDEO_URL and no GITHUB_REPOSITORY"}
            print("Instagram skipped: no public video URL available.")
    else:
        results["instagram"] = {"status": "skipped", "reason": "IG_USER_ID or IG_ACCESS_TOKEN is missing"}
        print("Instagram skipped: IG_USER_ID / IG_ACCESS_TOKEN not configured.")

    (OUT / "publish_result.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
