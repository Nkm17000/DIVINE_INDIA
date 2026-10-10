#!/usr/bin/env python3
"""Apply rotating camera-motion effects and the supplied Smart Learning Lab logo.

Effects rotate across generated reels in deterministic sorted order. Original audio is
preserved. Video geometry is kept fixed and logo overlay is added top-left.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

EFFECTS = [
    ("zoom_in_upward_drift", "min(1+on/900*0.50,2)", "iw/2-iw/zoom/2", "(ih-ih/zoom)*(1-on/900)"),
    ("upward_movement", "1.12", "iw/2-iw/zoom/2", "ih/2-ih/zoom/2-on*0.55"),
    ("zoom_out", "max(1.0,1.55-on/900*0.55)", "iw/2-iw/zoom/2", "ih/2-ih/zoom/2"),
    ("pan_left_to_right", "1.18", "(iw-iw/zoom)*(on/900)", "ih/2-ih/zoom/2"),
    ("pan_right_to_left", "1.18", "(iw-iw/zoom)*(1-on/900)", "ih/2-ih/zoom/2"),
    ("diagonal_movement", "1.22", "(iw-iw/zoom)*(on/900)", "(ih-ih/zoom)*(on/900)"),
    ("zoom_in_left", "min(1+on/900*0.50,2)", "(iw-iw/zoom)*(1-on/900)", "ih/2-ih/zoom/2"),
    ("zoom_out_upward", "max(1.0,1.50-on/900*0.50)", "iw/2-iw/zoom/2", "(ih-ih/zoom)*(1-on/900)"),
]

def run(cmd):
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input-dir', default='output')
    p.add_argument('--logo', default='assets/smart_learning_lab_logo.png')
    p.add_argument('--zoom-per-second', type=float, default=0.05, help='Maximum zoom increase per second for zoom-in effects')
    args = p.parse_args()
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        print('ERROR: ffmpeg and ffprobe are required.', file=sys.stderr); return 2
    root, logo = Path(args.input_dir), Path(args.logo)
    if not logo.exists():
        print(f'ERROR: logo not found: {logo}', file=sys.stderr); return 2
    videos = sorted(v for v in root.glob('*/daily_reel*.mp4') if v.is_file() and '.motiontmp' not in v.name)
    if not videos:
        print(f'No generated MP4 reels found under {root}/<folder>/.'); return 0
    successes, failures = 0, []
    for idx, video in enumerate(videos):
        temp = video.with_name(video.stem + '.motiontmp.mp4')
        effect_name, z, x, y = EFFECTS[idx % len(EFFECTS)]
        try:
            data = json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(video)]).stdout)
            if not data.get('streams'): raise RuntimeError('No video stream found')
            width, height = int(data['streams'][0]['width']), int(data['streams'][0]['height'])
            # zoompan's per-frame increment is based on a 30fps, 30-second reference;
            # the selected motion expression stays bounded and avoids black borders.
            zoom_expr = z
            if effect_name in ('zoom_in_upward_drift','zoom_in_left'):
                rate = max(0.0, min(args.zoom_per_second, 0.05))
                zoom_expr = f"min(1+on/30*{rate:.5f},2)"
            elif effect_name == 'zoom_out': zoom_expr = 'max(1.0,1.55-on/900*0.55)'
            elif effect_name == 'zoom_out_upward': zoom_expr = 'max(1.0,1.50-on/900*0.50)'
            vf = (
                f"zoompan=z='{zoom_expr}':x='{x}':y='{y}':d=1:s={width}x{height}:fps=30,"
                "setsar=1,format=yuv420p"
            )
            # Use the supplied logo image, placed top-left with a modest size and margin.
            filter_complex = (
                f"[0:v]{vf}[motion];"
                f"[1:v]scale=w='min(260,iw)':h=-1,format=rgba,colorchannelmixer=aa=0.96[brand];"
                f"[motion][brand]overlay=x=32:y=32:format=auto[outv]"
            )
            run(['ffmpeg','-y','-i',str(video),'-loop','1','-i',str(logo),'-filter_complex',filter_complex,
                 '-map','[outv]','-map','0:a?','-c:v','libx264','-preset','veryfast','-crf','21',
                 '-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart',str(temp)])
            if not temp.exists() or temp.stat().st_size == 0: raise RuntimeError('ffmpeg did not create output')
            temp.replace(video); successes += 1
            print(f'MOTION_APPLIED: {video} effect={effect_name} logo=top-left')
        except Exception as exc:
            if temp.exists(): temp.unlink()
            failures.append((video,str(exc))); print(f'MOTION_FAILED: {video}: {exc}',file=sys.stderr)
    print(f'MOTION SUMMARY: {successes} succeeded, {len(failures)} failed')
    return 1 if failures else 0

if __name__ == '__main__': raise SystemExit(main())
