#!/usr/bin/env python3
"""Create a single continuous, smooth diagonal devotional reel.

Vertical source image: top -> center-left -> bottom -> center-right -> top.
Landscape source image: left -> center-top -> right -> center-bottom -> left.
The motion uses a smooth sinusoidal path with no segment cuts or pauses.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

W, H, FPS = 1080, 1920, 30
# Gentle zoom-only animation for clips shorter than 10 seconds.
SHORT_VIDEO_ZOOM = 1.16
SHORT_VIDEO_ZOOM_RANGE = 0.06
SHORT_VIDEO_THRESHOLD_SECONDS = 10.0
# Longer clips keep the existing diagonal pan at a steady, moderate pace.
PAN_ZOOM = 1.22
PAN_CYCLE_SECONDS = 30.0


def run(cmd: list[str]) -> None:
    print(">", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height,duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def media_duration(path: Path) -> float:
    data = probe(path)
    durations = []
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio" and stream.get("duration"):
            durations.append(float(stream["duration"]))
    if data.get("format", {}).get("duration"):
        durations.append(float(data["format"]["duration"]))
    if not durations:
        raise RuntimeError(f"Could not determine media duration: {path}")
    return max(durations)


def image_dimensions(path: Path) -> tuple[int, int]:
    data = probe(path)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            return int(stream["width"]), int(stream["height"])
    raise RuntimeError(f"Could not determine image dimensions: {path}")


def vf_for(image: Path, duration: float, width: int, height: int, fps: int) -> str:
    """Build a continuous looped path; `on` is the output-frame counter."""
    iw, ih = image_dimensions(image)
    frames = max(2, math.ceil(duration * fps))
    # Scale up without cropping: zoompan needs spare source area to pan over.
    # `increase` guarantees enough pixels to cover the portrait output.
    base = f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase"
    # Clips under 10 seconds use zoom only: keep the framing centered and
    # animate one gentle zoom-in then zoom-out pulse, with no diagonal panning.
    if duration < SHORT_VIDEO_THRESHOLD_SECONDS:
        zoom = (
            f"{SHORT_VIDEO_ZOOM}+{SHORT_VIDEO_ZOOM_RANGE}*"
            f"(0.5-0.5*cos(2*PI*on/{frames:.6f}))"
        )
        x = "(iw-iw/zoom)*0.5"
        y = "(ih-ih/zoom)*0.5"
        zoom_mode = "centered zoom-in then zoom-out only"
    else:
        # Longer clips keep the established diagonal route. A fixed zoom and
        # one full cycle over ~1.25x the clip duration keeps motion unhurried
        # and consistently paced without zoom pulsing or end-of-video jumps.
        phase = f"(2*PI*on/{max(2, int(round(PAN_CYCLE_SECONDS * fps))):.6f})"
        zoom = str(PAN_ZOOM)
        if ih >= iw:  # vertical: top -> center-left -> bottom -> center-right -> top
            x = f"(iw-iw/zoom)*(0.50+0.22*sin({phase}))"
            y = f"(ih-ih/zoom)*(0.50-0.50*cos({phase}))"
        else:  # horizontal: left -> center-top -> right -> center-bottom -> left
            x = f"(iw-iw/zoom)*(0.50-0.50*cos({phase}))"
            y = f"(ih-ih/zoom)*(0.50-0.22*sin({phase}))"
        zoom_mode = "steady diagonal movement at moderate pace"
    return (
        f"{base},zoompan=z='{zoom}':x='{x}':y='{y}':d=1:"
        f"s={width}x{height}:fps={fps},setsar=1,format=yuv420p"
    )


def create_video(
    image: Path,
    audio: Path,
    output: Path,
    seed: int | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: int = FPS,
    max_seconds: float | None = None,
) -> dict:
    """Render a single uninterrupted video, with video length matched to audio."""
    image, audio, output = image.resolve(), audio.resolve(), output.resolve()
    if not image.is_file():
        raise FileNotFoundError(f"Image not found: {image}")
    if not audio.is_file():
        raise FileNotFoundError(f"Audio not found: {audio}")
    # Match the output orientation to the source image unless explicit dimensions were supplied.
    iw, ih = image_dimensions(image)
    if width is None and height is None:
        width, height = (W, H) if ih >= iw else (1920, 1080)
    elif width is None or height is None:
        raise ValueError("Specify both width and height, or neither for automatic orientation.")
    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("Width, height and FPS must be positive.")
    duration = media_duration(audio)
    if max_seconds is not None:
        duration = min(duration, max_seconds)
    if duration <= 0:
        raise RuntimeError(f"Audio duration is invalid: {duration}")
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = vf_for(image, duration, width, height, fps)
    # One ffmpeg render only: no segment boundaries, concatenation or direction jumps.
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", str(fps), "-i", str(image),
        "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
        "-vf", vf, "-t", f"{duration:.6f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-shortest", "-movflags", "+faststart", str(output),
    ])
    return {
        "image": str(image), "audio": str(audio), "output": str(output),
        "duration_seconds": round(duration, 3),
        "width": width, "height": height, "fps": fps,
        "movement": ("centered zoom only" if duration < SHORT_VIDEO_THRESHOLD_SECONDS else "continuous diagonal pan at a steady moderate pace"),
        "zoom_effect": (
            "centered zoom-in then zoom-out only"
            if duration < SHORT_VIDEO_THRESHOLD_SECONDS
            else "steady diagonal movement at moderate pace"
        ),
        "orientation": "vertical" if image_dimensions(image)[1] >= image_dimensions(image)[0] else "horizontal",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, help="Accepted for backwards compatibility; motion is deterministic.")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--fps", type=int, default=FPS)
    parser.add_argument("--max-seconds", type=float, help="Optional cap for short test renders.")
    args = parser.parse_args()
    print(json.dumps(create_video(args.image, args.audio, args.output, args.seed,
                                  args.width, args.height, args.fps, args.max_seconds),
                     indent=2))
