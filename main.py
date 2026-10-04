import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.rotation import choose_pair
from src.video import make_video
from src.caption import make_caption
from src.config import OUTPUT_DIR, STATE_FILE

ROOT = Path(__file__).resolve().parent

IMAGE_EXTS={".png",".jpg",".jpeg",".webp"}
AUDIO_EXTS={".mp3",".m4a",".wav",".aac",".ogg"}

# Supports the repository's existing images/audio folders AND the newer
# assets/images + assets/ringtones layout.
def find_media_dir(kind):
    if kind == "image":
        candidates=[ROOT/"images", ROOT/"assets"/"images"]
    else:
        candidates=[ROOT/"audio", ROOT/"ringtones", ROOT/"assets"/"ringtones", ROOT/"assets"/"audio"]
    for folder in candidates:
        if folder.is_dir() and any(p.is_file() for p in folder.iterdir()):
            return folder
    # Last-resort recursive discovery, excluding generated output/state/.git.
    wanted=IMAGE_EXTS if kind=="image" else AUDIO_EXTS
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix.lower() in wanted:
            if any(part in {".git","output","state","__pycache__"} for part in p.parts):
                continue
            return p.parent
    return candidates[0]

def media_files(folder, exts):
    if not folder.exists():
        return []
    return sorted([p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts])

def main():
    image_dir=find_media_dir("image")
    audio_dir=find_media_dir("audio")
    images=media_files(image_dir,IMAGE_EXTS)
    audios=media_files(audio_dir,AUDIO_EXTS)

    print(f"Image directory: {image_dir}")
    print(f"Audio directory: {audio_dir}")
    print(f"Images found: {len(images)}")
    print(f"Audio found : {len(audios)}")

    if not images or not audios:
        raise RuntimeError(
            "No media found. Put images in images/ (or assets/images/) and "
            "MP3s in audio/ (or assets/ringtones/)."
        )

    image_name,audio_name,state=choose_pair(images,audios,ROOT/STATE_FILE)
    image=str(image_dir/image_name)
    audio=str(audio_dir/audio_name)
    output=str(ROOT/OUTPUT_DIR/"daily_reel.mp4")
    caption=make_caption()

    print(f"Selected image : {image_name}")
    print(f"Selected audio : {audio_name}")
    print(f"Pairs used     : {len(state['used_pairs'])}/{len(images)*len(audios)}")
    print(f"Pair cycle     : {state['total_pairs_completed']}")
    print("Creating 5-segment moving video...")
    make_video(image,audio,output)

    selection={"image":image_name,"audio":audio_name,"caption":caption}
    out=ROOT/OUTPUT_DIR
    out.mkdir(parents=True,exist_ok=True)
    (out/"caption.txt").write_text(caption,encoding="utf-8")
    (out/"selection.json").write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Video ready:",output)

if __name__=="__main__":
    main()
