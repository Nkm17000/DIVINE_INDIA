import json
import random
import subprocess
import tempfile
from pathlib import Path
from .config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS, MAX_DURATION


def duration_seconds(audio):
    cmd=["ffprobe","-v","error","-show_entries","format=duration","-of","json",audio]
    data=json.loads(subprocess.check_output(cmd,text=True))
    return max(15.0,min(float(data["format"]["duration"]),MAX_DURATION))


def run(cmd):
    print(">", " ".join(map(str,cmd)))
    subprocess.run(cmd,check=True)


def make_segment(image,out,effect,duration):
    # Each segment is generated from the SAME source image. Only the camera
    # motion changes. This is what makes the still image feel like video.
    frames=max(2,int(duration*FPS))
    n=max(1,frames-1)
    if effect=="zoom_in":
        z=f"min(1+0.12*on/{n},1.12)"
        x="(iw-iw/zoom)/2"
        y="(ih-ih/zoom)/2-0.035*ih*on/"+str(n)
    elif effect=="zoom_out":
        z=f"max(1.12-0.12*on/{n},1.0)"
        x="(iw-iw/zoom)/2"
        y="(ih-ih/zoom)/2+0.02*ih*on/"+str(n)
    elif effect=="pan_lr":
        z="1.10"
        x=f"(iw-iw/zoom)*on/{n}"
        y="(ih-ih/zoom)/2"
    elif effect=="pan_rl":
        z="1.10"
        x=f"(iw-iw/zoom)*(1-on/{n})"
        y="(ih-ih/zoom)/2"
    else:
        z=f"min(1+0.07*on/{n},1.07)"
        x=f"(iw-iw/zoom)*on/{n}"
        y=f"(ih-ih/zoom)*(1-on/{n})"

    # Fill the vertical frame while retaining the original image content.
    vf=(
        f"scale=2160:3840:force_original_aspect_ratio=increase,"
        f"crop=2160:3840,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS},"
        f"setsar=1,format=yuv420p,"
        f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(0,duration-0.45):.3f}:d=0.45"
    )
    run([
        "ffmpeg","-y","-hide_banner","-loglevel","error",
        "-loop","1","-i",str(image),"-vf",vf,"-t",f"{duration:.3f}",
        "-an","-c:v","libx264","-preset","medium","-crf","21",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(out)
    ])


def make_video(image,audio,output):
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    total=duration_seconds(audio)
    # Exactly five motion segments. For short audio, each segment still has
    # enough time to show visible movement; for long audio, all five segments
    # are extended evenly while preserving the 5-effect structure.
    segment_duration=total/5.0
    effects=["zoom_in","zoom_out","pan_lr","pan_rl","diagonal"]
    random.SystemRandom().shuffle(effects)

    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        segments=[]
        for i,effect in enumerate(effects,1):
            seg=td/f"segment_{i}.mp4"
            print(f"Segment {i}/5: {effect} ({segment_duration:.2f}s)")
            make_segment(image,seg,effect,segment_duration)
            segments.append(seg)

        concat=td/"concat.txt"
        concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments),encoding="utf-8")
        joined=td/"joined.mp4"
        run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(joined)])

        # Reuse the same ringtone; loop it if needed and trim exactly to video.
        run([
            "ffmpeg","-y","-hide_banner","-loglevel","error",
            "-i",str(joined),"-stream_loop","-1","-i",str(audio),
            "-map","0:v:0","-map","1:a:0","-t",f"{total:.3f}",
            "-c:v","copy","-c:a","aac","-b:a","192k","-ar","44100",
            "-shortest","-movflags","+faststart",str(output)
        ])
    return output
