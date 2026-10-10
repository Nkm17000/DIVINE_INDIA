# Progressive zoom effect

The workflow now runs `src/apply_zoom_effect.py` immediately after `src/main.py` generates reels. It applies a centered zoom that grows by approximately 5% of the original scale per second, capped at 2x, and preserves the original audio track. It re-encodes generated MP4s with ffmpeg before the publish jobs upload the shared output artifact.

The helper expects generated files at `output/<folder>/daily_reel*.mp4`. Ubuntu GitHub runners install ffmpeg in the workflow. The zoom helper is a post-processing step; it does not replace the project's existing image/ringtone selection or video-generation code.
