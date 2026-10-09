# DIVINE INDIA — Folder-Matched Devotional Reels

## What it does

- Generates one MP4 per eligible folder present under both `images/` and `rings/`.
- Selects images and audio only from the same exact folder name.
- Uses continuous diagonal movement for vertical and horizontal images.
- Matches video duration to the selected audio duration.
- Saves used image/audio combinations in `state/rotation_state.json` and avoids repeating a pair until all eligible combinations for that folder have been used.
- Does not require Cloudflare.
- Publishes each generated folder's video only to the Facebook and Instagram accounts mapped to that folder in `config/social_accounts.json`.
- Runs a daily cleanup workflow for old generated Actions artifacts and temporary releases; source media and rotation history are preserved.

## Folder layout

```text
images/hanumanji/       rings/hanumanji/
images/shreekrishna/    rings/shreekrishna/
images/shyambaba/       rings/shyambaba/
images/maadurga/        rings/maadurga/
```

The folder names under `images/` and `rings/` must match exactly.

## Configure accounts in one JSON file

Edit `config/social_accounts.json`. You only configure which folder names each account should publish to. Credentials are stored once as GitHub Secrets and can be shared by multiple folders.

Example:

```json
{
  "facebook": {
    "FB_PAGE_KEY": ["hanumanji", "shreekrishna"],
    "FB_PAGE_KEY_2": ["hanumanji"]
  },
  "instagram": {
    "INSTA_PAGE_KEY": ["hanumanji", "shreekrishna"],
    "INSTA_PAGE_KEY_2": ["shreekrishna"]
  }
}
```

This means:

- Facebook account 1 publishes to `hanumanji` and `shreekrishna`.
- Facebook account 2 publishes only to `hanumanji`.
- Instagram account 1 publishes to `hanumanji` and `shreekrishna`.
- Instagram account 2 publishes only to `shreekrishna`.

Folder names must match the actual folder names exactly. To stop an account from publishing to a folder, remove that folder name from its array. To add another account, add another key such as `FB_PAGE_KEY_3` or `INSTA_PAGE_KEY_3` and its folder array.

## Add credentials to GitHub Secrets

Open **GitHub repository → Settings → Secrets and variables → Actions → New repository secret**.

For each Facebook account, add:

| GitHub Secret | Value |
|---|---|
| `FB_PAGE_KEY` | Facebook Page ID |
| `FB_PAGE_TOKEN` | Access token for that Page |
| `FB_PAGE_KEY_2` | Second Facebook Page ID |
| `FB_PAGE_TOKEN_2` | Second Page access token |
| `FB_PAGE_KEY_3` | Third Facebook Page ID, if used |
| `FB_PAGE_TOKEN_3` | Third Page access token, if used |

For each Instagram account, add:

| GitHub Secret | Value |
|---|---|
| `INSTA_PAGE_KEY` | Instagram professional account ID |
| `INSTA_PAGE_TOKEN` | Access token for that Instagram account |
| `INSTA_PAGE_KEY_2` | Second Instagram professional account ID |
| `INSTA_PAGE_TOKEN_2` | Second Instagram access token |
| `INSTA_PAGE_KEY_3` | Third Instagram account ID, if used |
| `INSTA_PAGE_TOKEN_3` | Third Instagram access token, if used |

**Important pairing rule:** `FB_PAGE_KEY` pairs with `FB_PAGE_TOKEN`; `FB_PAGE_KEY_2` pairs with `FB_PAGE_TOKEN_2`. Likewise, `INSTA_PAGE_KEY` pairs with `INSTA_PAGE_TOKEN`, and `_2` pairs with `_2`. Do not put actual IDs or tokens in the JSON file. The workflow explicitly maps up to 10 account slots per platform to environment variables; add secrets only for account slots you use.

If only one Facebook account and one Instagram account are used, you only need these four secrets: `FB_PAGE_KEY`, `FB_PAGE_TOKEN`, `INSTA_PAGE_KEY`, and `INSTA_PAGE_TOKEN`. A single account can be assigned to as many folders as you want in the JSON without duplicating credentials.

## Media selection and fallback

Files are sorted by filename. If a folder contains **more than 20** images or audio files, the first 10 and last 10 are excluded from selection. If it contains **20 or fewer**, all files are eligible so a video can still be generated. The combination history is tracked per folder and persists between workflow runs. Keep `state/rotation_state.json` committed; it must not be removed during cleanup.

## GitHub Actions

The `Daily Divine India Reels` workflow supports manual execution, push to `main`, and scheduled runs at 6:00 AM and 6:00 PM India Standard Time. It installs FFmpeg and Python dependencies, generates videos, publishes them to configured accounts, and commits rotation history.

The `Daily Generated Artifact Cleanup` workflow runs daily and can be triggered manually. It removes generated GitHub Actions artifacts and temporary `daily-reel-*` releases older than 24 hours. It does **not** delete images, ringtone files, source code, configuration, or rotation history.

### Instagram URL requirement

Instagram Reels publishing needs a publicly downloadable HTTPS video URL. The current workflow temporarily uses GitHub Release assets for that purpose; with this approach, the GitHub repository must be public. Temporary releases are deleted after publishing and stale releases are removed by cleanup.

## Run locally

Requires Python 3.12 and FFmpeg/ffprobe.

```bash
python -m pip install -r requirements.txt
python src/main.py
```

To run tests:

```bash
python -m unittest discover -s tests -v
```

## Troubleshooting

- If an account is skipped, verify both its ID/key and token secrets exist and that the JSON key names match the secret names.
- If a folder does not publish, confirm its exact name appears in the appropriate `facebook` or `instagram` array.
- If a folder is skipped during generation, check for matching folders under both `images/` and `rings/` and at least one supported image/audio file.
- Supported images: JPG, JPEG, PNG, WEBP. Supported audio: MP3, M4A, WAV, AAC, OGG, FLAC.
- Never print or commit access tokens.
