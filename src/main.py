#!/usr/bin/env python3
from __future__ import annotations
import json, os, random, hashlib
from datetime import datetime, timezone
from pathlib import Path
from video import create_video

ROOT=Path(__file__).resolve().parents[1]
STATE_FILE=ROOT/"state/rotation_state.json"
OUT=ROOT/"output/daily_reel.mp4"

IMAGE_EXTS={".jpg",".jpeg",".png",".webp"}
AUDIO_EXTS={".mp3",".m4a",".wav",".aac"}

def find_media(candidates, exts):
    for folder in candidates:
        if folder.exists() and folder.is_dir():
            found=sorted(
                p for p in folder.rglob("*")
                if p.is_file() and p.suffix.lower() in exts
            )
            if found:
                return found, folder
    return [], candidates[0]

def media_files(folder, exts):
    if not folder.exists():
        return []
    return sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in exts
    )

def load_state():
    default={"used_images":[],"used_audio":[],"used_pairs":[],"cycle":0,"last_selection":None}
    if not STATE_FILE.exists():
        return default
    try:
        raw=json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARNING: Could not read rotation state; starting fresh: {exc}")
        return default
    if not isinstance(raw, dict):
        return default
    # Backward-compatible migration: older versions may have stored pair names
    # as strings such as "image.jpg|ringtone.mp3" instead of dictionaries.
    pairs=[]
    for item in raw.get("used_pairs", []):
        if isinstance(item, dict):
            image=item.get("image")
            audio=item.get("audio")
            if image and audio:
                pairs.append({"image":str(image),"audio":str(audio)})
        elif isinstance(item, str):
            # Accept common legacy formats.
            if "|" in item:
                image,audio=item.split("|",1)
                if image and audio:
                    pairs.append({"image":image,"audio":audio})
            elif "," in item:
                image,audio=item.split(",",1)
                if image and audio:
                    pairs.append({"image":image.strip(),"audio":audio.strip()})
    images=[str(x) for x in raw.get("used_images",[]) if isinstance(x,(str,int))]
    audio=[str(x) for x in raw.get("used_audio",[]) if isinstance(x,(str,int))]
    return {
        "used_images":images,
        "used_audio":audio,
        "used_pairs":pairs,
        "cycle":int(raw.get("cycle",0) or 0),
        "last_selection":raw.get("last_selection") if isinstance(raw.get("last_selection"),dict) else None
    }

def save_state(s):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")

def pick_unique(items, used):
    available=[p for p in items if p.name not in used]
    if not available:
        used.clear()
        available=items[:]
    return random.choice(available)

def select_pair(images,audios,state):
    if not images or not audios:
        raise RuntimeError(
            "No media found. Supported layouts are images/ + audio/ "
            "or assets/images/ + assets/ringtones/."
        )

    total=len(images)*len(audios)
    if len(state["used_pairs"]) >= total:
        state["used_pairs"]=[]
        state["cycle"]+=1
        state["used_images"]=[]
        state["used_audio"]=[]

    used_pairs={(x.get("image"),x.get("audio")) for x in state["used_pairs"]}

    # Use every image once before repeating images.
    unused_images=[p for p in images if p.name not in state["used_images"]]
    if not unused_images:
        state["used_images"]=[]
        unused_images=images[:]

    # Use every ringtone once before repeating ringtones.
    unused_audio=[p for p in audios if p.name not in state["used_audio"]]
    if not unused_audio:
        state["used_audio"]=[]
        unused_audio=audios[:]

    # Try to satisfy all three goals: fresh image, fresh audio, unused pair.
    choices=[
        (im,au)
        for im in unused_images
        for au in unused_audio
        if (im.name,au.name) not in used_pairs
    ]
    if choices:
        image,audio=random.choice(choices)
    else:
        # After one media set is exhausted, preserve pair uniqueness.
        choices=[
            (im,au)
            for im in unused_images
            for au in audios
            if (im.name,au.name) not in used_pairs
        ]
        if not choices:
            choices=[
                (im,au)
                for im in images
                for au in unused_audio
                if (im.name,au.name) not in used_pairs
            ]
        if not choices:
            # Should only be reachable at the exact end of a combination cycle.
            state["used_pairs"]=[]
            state["cycle"]+=1
            image=random.choice(images)
            audio=random.choice(audios)
        else:
            image,audio=random.choice(choices)

    pair={"image":image.name,"audio":audio.name}
    state["used_images"].append(image.name)
    state["used_audio"].append(audio.name)
    state["used_pairs"].append(pair)
    state["last_selection"]=pair
    return image,audio

def main():
    images,_=find_media([
        ROOT/"images",
        ROOT/"assets/images",
        ROOT/"image",
        ROOT/"assets"
    ],IMAGE_EXTS)
    audios,_=find_media([
        ROOT/"audio",
        ROOT/"ringtones",
        ROOT/"assets/ringtones",
        ROOT/"assets/audio",
        ROOT/"music",
        ROOT/"assets"
    ],AUDIO_EXTS)

    print(f"Found {len(images)} image(s) and {len(audios)} audio file(s).")
    state=load_state()
    image,audio=select_pair(images,audios,state)

    seed=int(hashlib.sha256(
        f'{datetime.now(timezone.utc).date()}-{image.name}-{audio.name}-{state["cycle"]}'.encode()
    ).hexdigest()[:8],16)

    effects=create_video(image,audio,OUT,seed)

    # Basic output sanity check: ensure a real video was created.
    import subprocess
    probe=subprocess.run([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,nb_frames",
        "-of","json",str(OUT)
    ],capture_output=True,text=True,check=True)
    info=json.loads(probe.stdout)["streams"][0]
    if int(info.get("width",0)) != 1080 or int(info.get("height",0)) != 1920:
        raise RuntimeError(f"Unexpected video size: {info}")
    if int(info.get("nb_frames",0)) < 400:
        raise RuntimeError(f"Video contains too few frames: {info}")

    save_state(state)

    caption=random.choice([
        "🙏 राधे राधे 🙏",
        "🦚 जय श्री कृष्ण 🦚",
        "🌸 जय श्री श्याम 🌸",
    ])
    caption += "\n\n#RadheRadhe #JaiShreeKrishna #JaiShreeShyam #Bhakti #Devotional"
    (ROOT/"output/caption.txt").write_text(caption,encoding="utf-8")
    (ROOT/"output/selection.json").write_text(json.dumps({
        **state["last_selection"],"cycle":state["cycle"],"effects":effects
    },ensure_ascii=False,indent=2),encoding="utf-8")
    print("VIDEO:",OUT)
    print("IMAGE:",image.name)
    print("AUDIO:",audio.name)
    print("EFFECTS:",effects)

if __name__=="__main__":
    main()
