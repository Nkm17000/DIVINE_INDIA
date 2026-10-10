# Account-specific publishing jobs

This update adds separate GitHub Actions job names for each configured account. Example names:

- `Facebook — FB_PAGE_KEY — hanumanji / daily_reel.mp4`
- `Facebook — FB_PAGE_KEY_2 — hanumanji / daily_reel.mp4`
- `Instagram — INSTA_PAGE_KEY — hanumanji / daily_reel.mp4`
- `Instagram — INSTA_PAGE_KEY_2 — hanumanji / daily_reel.mp4`

Video generation happens once. The generated artifact is reused by the account-specific publishing jobs. Each job publishes to exactly one account, writes its own JSON result, and fails visibly if publishing fails or credentials are missing.
