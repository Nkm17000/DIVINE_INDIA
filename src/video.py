#!/usr/bin/env python3
"""
Create a devotional reel from ONE image + ONE MP3.

The image is deliberately reused 5 times, but every segment has a different
motion effect. This makes a single still image feel like a moving video.

Effects:
1. Slow zoom in + slight upward drift
2. Slow zoom out + slight left drift
3. Pan left -> right
4. Pan right -> left
5. Diagonal drift + gentle zoom

The effect order is shuffled per video, while never repeating an effect inside
the same video.
"""
from __future__ import annotations

import argparse
import random
import subprocess
import tempfile
from pathlib import Path

W, H = 1080, 1920
SEGMENT_SECONDS = 3
FPS = 30
EFFECTS = ["zoom_in", "zoom_out", "pan_lr", "pan_rl", "diagonal"]

def run(cmd: list[str]) -> None:
    print(">", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)

def make_segment(image: Path, out: Path, effect: str, seed: int) -> None:
    # Large canvas first gives zoom/pan room without exposing edges.
    # zoompan renders the complete segment directly from the same source image, avoiding black transition frames.
    # z: zoom level; x/y: crop origin.
    if effect == "zoom_in":
        z = "min(zoom+0.0018,1.18)"
        x = "(iw-iw/zoom)/2"
        y = "(ih-ih/zoom)/2-18"
    elif effect == "zoom_out":
        z = "max(zoom-0.0018,1.0)"
        x = "(iw-iw/zoom)/2"
        y = "(ih-ih/zoom)/2"
    elif effect == "pan_lr":
        z = "1.10"
        x = "(iw-iw/zoom)*(on/(180-1))"
        y = "(ih-ih/zoom)/2"
    elif effect == "pan_rl":
        z = "1.10"
        x = "(iw-iw/zoom)*(1-on/(180-1))"
        y = "(ih-ih/zoom)/2"
    else:  # diagonal
        z = "min(1.02+on*0.0009,1.16)"
        x = "(iw-iw/zoom)*(on/(180-1))"
        y = "(ih-ih/zoom)*(1-on/(180-1))"

    # Render the complete segment: 90 frames = 3 seconds at 30fps.
    vf = (
        f"scale=2160:3840:force_original_aspect_ratio=increase,"
        f"crop=2160:3840,"
        f"zoompan=z='{z}':x='{x}':y='{y}':"
        f"d={SEGMENT_SECONDS*FPS}:s={W}x{H}:fps={FPS},"
        f"setsar=1,format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", str(image),
        "-vf", vf,
        "-frames:v", str(SEGMENT_SECONDS*FPS),
        "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-movflags", "+faststart", str(out)
    ])

def create_video(image: Path, audio: Path, output: Path, seed: int | None = None) -> list[str]:
    output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed if seed is not None else random.randrange(1_000_000_000))
    effects = EFFECTS[:]
    rng.shuffle(effects)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        segments=[]
        for i, effect in enumerate(effects):
            seg=td/f"segment_{i+1}.mp4"
            make_segment(image, seg, effect, rng.randrange(1_000_000_000))
            segments.append(seg)

        concat_file=td/"concat.txt"
        concat_file.write_text(
            "".join(f"file '{p.as_posix()}'\n" for p in segments),
            encoding="utf-8"
        )
        joined=td/"joined.mp4"
        run([
            "ffmpeg","-y","-hide_banner","-loglevel","error",
            "-f","concat","-safe","0","-i",str(concat_file),
            "-c:v","libx264","-preset","medium","-crf","20",
            "-pix_fmt","yuv420p","-r",str(FPS),
            "-an",str(joined)
        ])

        # Match video length to the selected ringtone. The audio is trimmed to
        # the video duration; if the ringtone is shorter it loops automatically.
        run([
            "ffmpeg","-y","-hide_banner","-loglevel","error",
            "-i",str(joined),"-stream_loop","-1","-i",str(audio),
            "-map","0:v:0","-map","1:a:0",
            "-t",str(SEGMENT_SECONDS*len(effects)),
            "-c:v","copy","-c:a","aac","-b:a","192k",
            "-shortest","-movflags","+faststart",str(output)
        ])
    return effects

if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--image",required=True,type=Path)
    ap.add_argument("--audio",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--seed",type=int)
    args=ap.parse_args()
    effects=create_video(args.image,args.audio,args.output,args.seed)
    print("EFFECTS:", ",".join(effects))
