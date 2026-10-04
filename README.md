# Daily Shyam / Krishna Moving Reel Publisher

This project turns one devotional image + one MP3 into a **real 9:16 MP4 video**. The image is not a static frame: FFmpeg creates a smooth Ken Burns-style zoom and gentle pan across the image while the selected devotional audio plays.

## What it does

Every run:

1. Selects one image and one ringtone/bhajan.
2. Prefers an image not used in the current image cycle.
3. Prefers audio not used in the current audio cycle.
4. Never repeats the same image + audio pair while an unused pair exists.
5. With 34 images and 20 audio files, there are **680 unique pairs**.
6. After all 680 pairs are used, pairing starts a new cycle and tries to create different pairings again.
7. Generates a 1080×1920 vertical MP4 with slow zoom + pan, fade in/out, and background fill.
8. Generates a devotional caption such as `जय श्री श्याम 🙏 | जय श्री कृष्ण 🙏 | Have a great day!`.
9. Publishes the same generated MP4 to Facebook and/or Instagram when the required credentials are configured.
10. If credentials are missing, **publishing is skipped and the video is still generated successfully**.

## Facebook / Instagram defaults

Publishing is enabled by default:

```text
POST_TO_FACEBOOK=true
POST_TO_INSTAGRAM=true
META_GRAPH_VERSION=v24.0
```

Credentials themselves default to empty values. This is intentional. Empty credentials mean **generate video only**.

### Facebook
Required:

```text
FB_PAGE_ID
FB_PAGE_ACCESS_TOKEN
```

If either is missing, Facebook is skipped.

### Instagram
Required:

```text
IG_USER_ID
IG_ACCESS_TOKEN
```

If either is missing, Instagram is skipped.

Instagram also needs a public HTTPS URL for the MP4. In GitHub Actions, when Instagram credentials are present, the workflow uploads the generated MP4 to a temporary GitHub Release and passes that URL to Meta.

## GitHub Actions

The workflow runs every day at **09:00 IST** and can also be started manually with `workflow_dispatch`.

The workflow always performs:

```text
Generate video → save output → optional publishing → save rotation state
```

It does **not** fail merely because Facebook or Instagram credentials are absent.

### GitHub Secrets

Add these only for the platforms you want to publish to:

```text
FB_PAGE_ID
FB_PAGE_ACCESS_TOKEN
IG_USER_ID
IG_ACCESS_TOKEN
```

You can configure only Facebook, only Instagram, both, or neither.

Optional repository variable:

```text
META_GRAPH_VERSION
```

If omitted, `v24.0` is used.

## Local usage

Install Python 3.11+ and FFmpeg.

```bash
pip install -r requirements.txt
python main.py
```

Generated files:

```text
output/daily_reel.mp4
output/selection.json
output/caption.txt
```

To attempt publishing locally:

```bash
python publish.py
```

Missing credentials will simply skip the corresponding platform.

## Video effect

The foreground image uses FFmpeg `zoompan` to create a continuous motion effect:

- slow zoom from approximately 1.00× to 1.08×
- gentle horizontal movement
- gentle vertical movement
- blurred enlarged background fills the 9:16 canvas
- smooth fade in and fade out
- AAC background audio
- H.264 MP4 with `+faststart`

This makes the image behave like a short video/reel rather than a static image.

## Project structure

```text
.
├── .github/workflows/daily-reel.yml
├── .editorconfig
├── .gitattributes
├── .gitignore
├── .env.example
├── LICENSE
├── README.md
├── requirements.txt
├── main.py
├── publish.py
├── images/
├── audio/
├── output/
├── state/
└── src/
    ├── caption.py
    ├── config.py
    ├── meta.py
    ├── rotation.py
    └── video.py
```

## Important

Only publish music and images you have permission to use. This project does not verify licensing of supplied media.
