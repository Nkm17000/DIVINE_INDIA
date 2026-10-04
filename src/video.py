#!/usr/bin/env python3
from __future__ import annotations
import argparse, math, random, subprocess, tempfile
from pathlib import Path

W,H,FPS=1080,1920,30
TOTAL_SECONDS=30
SEGMENTS=8
SEGMENT_SECONDS=TOTAL_SECONDS/SEGMENTS
FRAMES=math.ceil(SEGMENT_SECONDS*FPS)

EFFECTS=["zoom_in_up","pan_up","zoom_out","pan_lr","pan_rl","diagonal","zoom_in_left","zoom_out_up"]

def run(cmd):
    print(">", " ".join(map(str,cmd)))
    subprocess.run(cmd,check=True)

def vf(effect):
    # zoompan exposes the output-frame counter as `on`. Use the known
    # segment length instead of N/d, which are not valid expression variables here.
    den=max(FRAMES-1, 1)
    if effect=="zoom_in_up":
        z=f"min(1.02+on*0.00095,1.135)"; x=f"(iw-iw/zoom)/2"; y=f"(ih-ih/zoom)*(0.58-0.10*on/{den})"
    elif effect=="pan_up":
        z=f"1.08"; x=f"(iw-iw/zoom)/2"; y=f"(ih-ih/zoom)*(0.72-0.44*on/{den})"
    elif effect=="zoom_out":
        z="max(1.14-on*0.00095,1.02)"; x="(iw-iw/zoom)/2"; y="(ih-ih/zoom)/2"
    elif effect=="pan_lr":
        z=f"1.08"; x=f"(iw-iw/zoom)*(0.08+0.84*on/{den})"; y=f"(ih-ih/zoom)/2"
    elif effect=="pan_rl":
        z=f"1.08"; x=f"(iw-iw/zoom)*(0.92-0.84*on/{den})"; y=f"(ih-ih/zoom)/2"
    elif effect=="diagonal":
        z=f"1.06+on*0.00045"; x=f"(iw-iw/zoom)*(0.10+0.65*on/{den})"; y=f"(ih-ih/zoom)*(0.65-0.50*on/{den})"
    elif effect=="zoom_in_left":
        z=f"min(1.02+on*0.00090,1.13)"; x=f"(iw-iw/zoom)*(0.78-0.50*on/{den})"; y=f"(ih-ih/zoom)/2"
    else:
        z=f"max(1.13-on*0.00090,1.02)"; x=f"(iw-iw/zoom)/2"; y=f"(ih-ih/zoom)*(0.65-0.30*on/{den})"
    return (f"scale=2160:3840:force_original_aspect_ratio=increase,"
            f"crop=2160:3840,zoompan=z='{z}':x='{x}':y='{y}':"
            f"d={FRAMES}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p")

def make_segment(image,out,effect):
    run(["ffmpeg","-y","-hide_banner","-loglevel","error","-loop","1","-i",str(image),
         "-vf",vf(effect),"-frames:v",str(FRAMES),"-an",
         "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
         "-movflags","+faststart",str(out)])

def create_video(image,audio,output,seed=None):
    rng=random.Random(seed if seed is not None else random.randrange(2**32))
    effects=EFFECTS[:]; rng.shuffle(effects)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); segs=[]
        for i,e in enumerate(effects):
            p=td/f"seg{i}.mp4"; make_segment(image,p,e); segs.append(p)
        concat=td/"concat.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in segs),encoding="utf-8")
        joined=td/"joined.mp4"
        run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","concat","-safe","0",
             "-i",str(concat),"-vf",f"fps={FPS},format=yuv420p","-t",str(TOTAL_SECONDS),
             "-an","-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
             "-movflags","+faststart",str(joined)])
        run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(joined),
             "-stream_loop","-1","-i",str(audio),"-map","0:v:0","-map","1:a:0",
             "-t",str(TOTAL_SECONDS),"-c:v","copy","-c:a","aac","-b:a","192k",
             "-ar","44100","-shortest","-movflags","+faststart",str(output)])
    return effects

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--image",required=True,type=Path); ap.add_argument("--audio",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path); ap.add_argument("--seed",type=int)
    a=ap.parse_args(); print("EFFECTS:",create_video(a.image,a.audio,a.output,a.seed))
