#!/usr/bin/env python3
from __future__ import annotations
import json, os, random, hashlib
from datetime import datetime, timezone
from pathlib import Path
from video import create_video

ROOT=Path(__file__).resolve().parents[1]
IMG_DIR=ROOT/"assets/images"
AUDIO_DIR=ROOT/"assets/ringtones"
STATE_FILE=ROOT/"state/rotation_state.json"
OUT=ROOT/"output/daily_reel.mp4"

def media_files(folder, exts):
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts])

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"used_images":[],"used_audio":[],"used_pairs":[],"cycle":0,"last_selection":None}

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
        raise RuntimeError("Add images to assets/images and MP3s to assets/ringtones.")

    # First priority: do not repeat an image or ringtone until each has been used.
    image=pick_unique(images,state["used_images"])
    audio=pick_unique(audios,state["used_audio"])

    pairs={(x.get("image"),x.get("audio")) for x in state["used_pairs"]}
    # Prefer a pair not used in the current full combination cycle.
    candidates=[a for a in audios if (image.name,a.name) not in pairs]
    if candidates:
        audio=random.choice(candidates)

    # If all combinations have been exhausted, start a new pair cycle while
    # keeping image/audio rotation independent.
    total=len(images)*len(audios)
    if len(state["used_pairs"]) >= total:
        state["used_pairs"]=[]
        state["cycle"]+=1
        audio=pick_unique(audios,state["used_audio"])

    pair={"image":image.name,"audio":audio.name}
    state["used_images"].append(image.name)
    state["used_audio"].append(audio.name)
    state["used_pairs"].append(pair)
    state["last_selection"]=pair
    return image,audio

def main():
    images=media_files(IMG_DIR,{".jpg",".jpeg",".png",".webp"})
    audios=media_files(AUDIO_DIR,{".mp3",".m4a",".wav"})
    state=load_state()
    image,audio=select_pair(images,audios,state)

    seed=int(hashlib.sha256(
        f'{datetime.now(timezone.utc).date()}-{image.name}-{audio.name}-{state["cycle"]}'.encode()
    ).hexdigest()[:8],16)

    effects=create_video(image,audio,OUT,seed)
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
