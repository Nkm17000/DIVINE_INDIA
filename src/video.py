import json
import subprocess
from pathlib import Path
from .config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS, MAX_DURATION


def duration_seconds(audio):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", audio]
    data = json.loads(subprocess.check_output(cmd, text=True))
    return max(3.0, min(float(data["format"]["duration"]), MAX_DURATION))


def make_video(image, audio, output):
    """Create a vertical reel where the still image behaves like moving video."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    duration = duration_seconds(audio)
    frames = max(1, int(duration * FPS))

    # Ken Burns effect: slowly zoom from 1.00x to 1.08x and gently pan.
    # zoompan produces a real frame sequence, so the still image is encoded
    # as motion video rather than a static slideshow frame.
    zoom_expr = "min(max(zoom,1.0)+0.0013,1.08)"
    x_expr = "iw/2-(iw/zoom/2)+0.04*iw*sin(2*PI*on/" + str(frames) + ")"
    y_expr = "ih/2-(ih/zoom/2)+0.03*ih*cos(2*PI*on/" + str(frames) + ")"

    vf = (
        f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},boxblur=28:12,eq=brightness=-0.04:saturation=1.05[bg];"
        f"[0:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black@0,"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d=1:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS},"
        f"format=rgba[fg];"
        f"[bg][fg]overlay=0:0,format=yuv420p,"
        f"fade=t=in:st=0:d=0.6,fade=t=out:st={max(0,duration-0.8):.3f}:d=0.8[v]"
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", image,
        "-stream_loop", "-1", "-i", audio,
        "-filter_complex", vf,
        "-map", "[v]", "-map", "1:a:0", "-r", str(FPS),
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-movflags", "+faststart", "-shortest", output,
    ]
    subprocess.run(cmd, check=True)
    return output
