# DIVINE INDIA — Folder-Matched Devotional Reels

## Critical media-matching guarantee

**The image and ringtone are always selected from folders with the exact same name.**
The generator reads only these pairs:

- `images/hanumanji/` + `rings/hanumanji/`
- `images/maadurga/` + `rings/maadurga/`
- `images/shreekrishna/` + `rings/shreekrishna/`
- `images/shyambaba/` + `rings/shyambaba/`

For every run, it generates one separate MP4 for each matching deity folder.
It never picks an image from one deity and a ringtone from another. Folder matching is
case-sensitive on GitHub's Linux runner. If a folder is missing on either side, it is
skipped with a warning rather than falling back to a different folder.

## Rotation

Each deity folder has its own rotation history in `state/rotation_state.json`.
The most recent 10 image/ringtone combinations for that folder are excluded from the next
selection whenever other combinations are available. If a folder has no alternative
combination outside its last 10, a repeat is mathematically unavoidable and the generator
logs the start of a new cycle. Different folders never share rotation history.

## Output

- `output/hanumanji/daily_reel.mp4`
- `output/maadurga/daily_reel.mp4`
- `output/shreekrishna/daily_reel.mp4`
- `output/shyambaba/daily_reel.mp4`

Each generated folder also has its own `caption.txt` and `selection.json`. For compatibility
with the existing single-destination publishing step, `output/daily_reel.mp4` is a copy of
the first generated folder's video. The GitHub Actions artifact includes all folder-specific
videos. Review/update the publishing workflow before assuming every folder-specific video is
being published to every social account.

## Run locally

Requires Python 3.12 and FFmpeg/ffprobe installed.

```bash
python -m pip install -r requirements.txt
python src/main.py
```

## GitHub Actions

The existing workflow supports manual run, push to `main`, and two scheduled runs per day
(6:00 AM and 6:00 PM India Standard Time). Python dependencies are installed from
`requirements.txt`; the workflow uploads generated MP4s and selection metadata as artifacts.

## Account configuration and credentials

Set publishing IDs/tokens as GitHub Actions secrets. Never commit access tokens to this
repository. Instagram's Graph API needs a publicly downloadable video URL and the relevant
Instagram professional-account permissions. Facebook publishing requires a Page ID and a
Page access token with video publishing permissions.

## Troubleshooting the folder match

If a folder is not processed, check that the exact same folder name exists under both
`images/` and `rings/`, and that each contains at least one supported image/audio file.
Supported images: JPG, JPEG, PNG, WEBP. Supported audio: MP3, M4A, WAV, AAC, OGG, FLAC.


## Continuous diagonal animation (updated)

The renderer now creates each reel in one FFmpeg pass instead of joining eight separate motion segments.
This removes segment cuts and direction-change freezes. Motion follows a continuous sinusoidal path:

- **Portrait/vertical image:** top → center-left → bottom → center-right → top.
- **Landscape/horizontal image:** left → center-top → right → center-bottom → left.

The direction changes are gradual and loop smoothly until the audio ends. The output duration is matched to the selected audio duration; audio is not silently looped or cut to a fixed 30-second duration. Image and audio are still selected only from the same deity folder.

Run a short local preview:

```bash
python src/video.py \
  --image "images/shreekrishna/Krishna and Arjuna at Dawn.png" \
  --audio "rings/shreekrishna/Krishna-Flute-Background-Music-Bansuri.mp3" \
  --output output/test-preview.mp4 --width 540 --height 960 --fps 24 --max-seconds 8
```

Omit `--max-seconds` for the full audio duration. Production defaults are 1080×1920 at 30 FPS.
