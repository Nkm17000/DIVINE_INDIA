# Camera motion and Smart Learning Lab logo

`src/apply_zoom_effect.py` preserves the original audio and overlays the supplied logo at the top-left. It rotates deterministically through eight camera-motion styles across sorted generated reels:

1. Zoom in + upward drift
2. Upward movement
3. Zoom out
4. Pan left to right
5. Pan right to left
6. Diagonal movement
7. Zoom in + left movement
8. Zoom out + upward movement

The two zoom-in styles use a configurable 5%/second zoom increase, capped at 2x. Other styles retain their own pan/zoom trajectories. The helper processes `output/<folder>/daily_reel*.mp4`; ffmpeg and ffprobe must be installed. The logo file is `assets/smart_learning_lab_logo.png`.

The workflow should invoke this helper after video generation and before uploading the shared generated-video artifact, so Facebook and Instagram jobs reuse the same processed reel. These motion effects are assigned across reels in sorted order; if you want each reel split into eight internal segments, that must be implemented in the video generator itself.
