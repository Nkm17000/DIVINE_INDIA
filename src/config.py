import os

VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
FPS = int(os.getenv("VIDEO_FPS", "30"))
MAX_DURATION = int(os.getenv("MAX_DURATION_SECONDS", "90"))
IMAGE_FIT = os.getenv("IMAGE_FIT", "contain")  # contain or cover
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
STATE_FILE = os.getenv("STATE_FILE", "state/rotation_state.json")

META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v24.0")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "") or FB_PAGE_ACCESS_TOKEN

POST_TO_FACEBOOK = os.getenv("POST_TO_FACEBOOK", "true").lower() == "true"
POST_TO_INSTAGRAM = os.getenv("POST_TO_INSTAGRAM", "true").lower() == "true"

PUBLIC_VIDEO_URL = os.getenv("PUBLIC_VIDEO_URL", "")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")
GITHUB_RELEASE_TAG = os.getenv("GITHUB_RELEASE_TAG", "daily-video")
GITHUB_RELEASE_ASSET = os.getenv("GITHUB_RELEASE_ASSET", "daily_reel.mp4")

CAPTION_PREFIX = os.getenv("CAPTION_PREFIX", "")
