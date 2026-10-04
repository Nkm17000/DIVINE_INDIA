# Shyam / Krishna Daily Moving Reel

One source image becomes a real animated 15-second vertical reel.

## Animation

The same image is reused across 5 x 3-second segments:
1. slow zoom in + upward drift
2. slow zoom out
3. left-to-right pan
4. right-to-left pan
5. diagonal drift + gentle zoom

The five effects are shuffled for every generated reel, so the effect order changes.

## Assets

Put images in `assets/images/` and MP3 files in `assets/ringtones/`.

## GitHub

The workflow runs on:
- manual `workflow_dispatch`
- push to `main`
- daily at 5:00 AM IST (`30 23 * * *` UTC)

The generated MP4 is ALWAYS uploaded as a GitHub Actions artifact, even when Meta posting is skipped or fails.

## Meta

FB/Instagram secrets are optional. Missing credentials never prevent video generation.

Instagram additionally needs a public MP4 URL for the Graph API. Set `INSTAGRAM_VIDEO_URL` if your workflow hosts the generated MP4 publicly before publishing.


## Black-screen fix

The animation renderer uses `zoompan` with `d=90` for each 3-second segment,
so each segment is rendered as a complete 90-frame sequence from the image.
There are no fade-to-black transitions. The five segments are concatenated
with continuous timestamps and re-encoded to avoid timestamp/keyframe gaps.


## Supported asset folders

The workflow automatically detects either:
- `images/` and `audio/`
- `assets/images/` and `assets/ringtones/`

It searches recursively inside those folders.
