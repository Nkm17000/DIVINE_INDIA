import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.rotation import choose_pair
from src.video import make_video
from src.caption import make_caption
from src.config import OUTPUT_DIR, STATE_FILE

ROOT=Path(__file__).resolve().parent
IMAGE_DIR=ROOT/"images"
AUDIO_DIR=ROOT/"audio"
OUT=ROOT/OUTPUT_DIR

def media_files(folder, exts):
    return sorted([p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts])

def main():
    images=media_files(IMAGE_DIR,{".png",".jpg",".jpeg",".webp"})
    audios=media_files(AUDIO_DIR,{".mp3",".m4a",".wav",".aac"})
    if not images or not audios:
        raise RuntimeError("No images or audio files found.")

    image_name,audio_name,state=choose_pair(images,audios,ROOT/STATE_FILE)
    image=str(IMAGE_DIR/image_name)
    audio=str(AUDIO_DIR/audio_name)
    output=str(OUT/"daily_reel.mp4")
    caption=make_caption()

    print(f"Selected image : {image_name}")
    print(f"Selected audio : {audio_name}")
    print(f"Pairs used     : {len(state['used_pairs'])}/{len(images)*len(audios)}")
    print(f"Pair cycle     : {state['total_pairs_completed']}")
    print("Creating video...")
    make_video(image,audio,output)

    selection={
        "image":image_name,
        "audio":audio_name,
        "caption":caption
    }
    (OUT/"caption.txt").write_text(caption,encoding="utf-8")
    (OUT/"selection.json").write_text(
        json.dumps(selection,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print("Video ready:",output)

if __name__=="__main__":
    main()
