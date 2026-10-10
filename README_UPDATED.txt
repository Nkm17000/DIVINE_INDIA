DIVINE INDIA — updated rotation and per-deity video counts

CHANGES
- Rotation tries recent-media exclusion windows in this order: last 10, last 7, last 3, last 1, then no recent-media exclusion if unavoidable. A valid folder is no longer skipped just because strict last-10 rotation is impossible.
- Image/ringtone pairs remain unique within a cycle until all available combinations have been used. When combinations run out, the cycle resets and the fallback rules still apply.
- Configure each deity name and video count directly in config/social_accounts.json; no separate deity video-count file is used.
- The first video is output/<deity>/daily_reel.mp4; further videos are daily_reel_2.mp4, daily_reel_3.mp4, etc. Workflow artifact/release URL creation and Facebook/Instagram publishing process all these clips.
- Facebook/Instagram profile URLs stay at config level in config/social_accounts.json; IDs and access tokens remain GitHub Secrets.

VIDEO COUNT CONFIG (inside the existing social_accounts.json)
{
  "facebook": {
    "FB_PAGE_KEY": {
      "folders": [
        {"name": "hanumanji", "count": 2},
        {"name": "shreekrishna", "count": 1},
        {"name": "maadurga", "count": 1},
        {"name": "shyambaba", "count": 1}
      ],
      "profile_url": "https://www.facebook.com/YOUR_PAGE"
    }
  },
  "instagram": {
    "INSTA_PAGE_KEY": {
      "folders": [
        {"name": "hanumanji", "count": 2},
        {"name": "shreekrishna", "count": 1},
        {"name": "maadurga", "count": 1},
        {"name": "shyambaba", "count": 1}
      ],
      "profile_url": "https://www.instagram.com/YOUR_PROFILE/"
    }
  }
}

The count is repeated under Facebook and Instagram so the existing account-to-folder mapping stays explicit. Keep each deity's count the same in both platform sections. Existing string-only folder entries remain supported and default to count 1.

REPOSITORY INTEGRATION
Copy the updated files/folders into the repository, preserving your existing media and other settings. Keep the actual account IDs/tokens in GitHub Secrets. The social_accounts.json included here reflects the requested URLs, four deity folders, and per-deity counts. Preserve any additional account mappings you already use, and keep counts consistent wherever a deity appears.

TESTING
Run: python -m unittest discover -s tests -v
The tests cover the fallback selection sequence, video count configuration, account URL configuration, and multi-video publishing URL lookup. Actual Meta publishing requires your GitHub credentials and is not performed by local tests.
