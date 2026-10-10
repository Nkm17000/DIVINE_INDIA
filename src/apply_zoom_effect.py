#!/usr/bin/env python3
"""Apply a centered progressive zoom to generated MP4 reels while preserving audio and adding a Smart Learning Lab label.

The zoom increases by approximately 5% of the original image scale per second,
with a 2x cap. Files are replaced only after ffmpeg completes successfully.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', default='output')
    parser.add_argument('--zoom-per-second', type=float, default=0.05)
    args = parser.parse_args()
    if shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None:
        print('ERROR: ffmpeg and ffprobe are required.', file=sys.stderr)
        return 2
    root = Path(args.input_dir)
    videos = sorted(p for p in root.glob('*/daily_reel*.mp4') if p.is_file() and not p.name.endswith('.zoomtmp.mp4'))
    if not videos:
        print(f'No generated MP4 reels found under {root}/<folder>/.')
        return 0
    # At 30 fps, add 5% of original scale per second; clamp to 2x.
    increment = max(0.0, min(args.zoom_per_second, 0.25)) / 30.0
    z_expr = f"min(zoom+{increment:.8f},2)"
    successes, failures = 0, []
    for video in videos:
        temp = video.with_name(video.stem + '.zoomtmp.mp4')
        try:
            probe = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', str(video)])
            streams = json.loads(probe.stdout).get('streams', [])
            if not streams:
                raise RuntimeError('No video stream found')
            width, height = int(streams[0]['width']), int(streams[0]['height'])
            # zoompan outputs the same frame size and maps original audio unchanged.
            # Apply the progressive zoom and add a consistent top-center brand label.
            # The label is a text watermark, not a platform/account identifier.
            vf = (
                f"zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps=30,"
                "drawtext=text='SMART LEARNING LAB':font='DejaVu Sans':fontcolor=white:fontsize=h*0.035:"
                "x=(w-text_w)/2:y=h*0.035:box=1:boxcolor=black@0.48:boxborderw=14,setsar=1"
            )
            run(['ffmpeg', '-y', '-i', str(video), '-vf', vf, '-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(temp)])
            if not temp.exists() or temp.stat().st_size == 0:
                raise RuntimeError('ffmpeg did not create output')
            temp.replace(video)
            successes += 1
            print(f'ZOOM_APPLIED: {video} (+{args.zoom_per_second:.0%}/second, capped at 2x)')
        except Exception as exc:
            if temp.exists():
                temp.unlink()
            failures.append((video, str(exc)))
            print(f'ZOOM_FAILED: {video}: {exc}', file=sys.stderr)
    print(f'ZOOM SUMMARY: {successes} succeeded, {len(failures)} failed')
    return 1 if failures else 0

if __name__ == '__main__':
    raise SystemExit(main())
