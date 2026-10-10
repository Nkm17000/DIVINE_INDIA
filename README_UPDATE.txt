DIVINE INDIA — platform-separated publishing patch

Files to replace/add:
- Replace src/publish.py with this version.
- Add .github/workflows/publish-facebook.yml.
- Add .github/workflows/publish-instagram.yml.

Publication tracking is written to:
- data/history/publication_history.json (append-only history, capped at 20,000 records)
- data/history/publication_status.json (latest result per platform/account/folder/video)

Each configured target is attempted independently. An error for one Facebook Page does not stop other Pages; Instagram runs in a separate workflow and is not gated on Facebook success. A non-zero workflow result is still returned if one or more targets fail, while the rest are attempted and their statuses are saved.

Important deployment note: both workflows currently generate videos in their own run, matching the existing daily-reel.yml architecture. They are serialized independently and therefore can select different rotation pairs if run at the same time. If both platforms must publish the exact same generated video in each cycle, the repository should use one shared generation workflow that uploads a video artifact and then triggers both platform publisher workflows from that artifact.

Schedules retained from the current workflow: 6:00 AM and 6:00 PM IST (00:30 and 12:30 UTC). GitHub Secrets are still expected as FB_PAGE_KEY / FB_PAGE_TOKEN and _2 through _10; Instagram uses INSTA_PAGE_KEY / INSTA_PAGE_TOKEN and _2 through _10.
