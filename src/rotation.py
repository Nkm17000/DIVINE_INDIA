import json, random
from pathlib import Path
from datetime import datetime, timezone

def _load(path):
    if Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "image_cycle": {"order": [], "pos": 0, "used": []},
        "audio_cycle": {"order": [], "pos": 0, "used": []},
        "used_pairs": [],
        "total_pairs_completed": 0,
        "last_selection": None,
        "history": []
    }

def _shuffle(items):
    items = list(items)
    random.SystemRandom().shuffle(items)
    return items

def _ensure_cycle(cycle, items):
    current = set(cycle.get("order", []))
    if len(cycle.get("order", [])) != len(items) or current != set(items) or len(cycle.get("used", [])) >= len(items):
        cycle["order"] = _shuffle(items)
        cycle["pos"] = 0
        cycle["used"] = []
    return cycle

def choose_pair(image_names, audio_names, state_path):
    path = Path(state_path)
    state = _load(path)

    # Once every possible pair has been used, start a brand-new pair cycle.
    all_pairs = len(image_names) * len(audio_names)
    if len(state["used_pairs"]) >= all_pairs:
        state["used_pairs"] = []
        state["total_pairs_completed"] = state.get("total_pairs_completed", 0) + 1

    ic = _ensure_cycle(state["image_cycle"], image_names)
    ac = _ensure_cycle(state["audio_cycle"], audio_names)

    used_pairs = set(state["used_pairs"])

    # Build candidates. First priority: unused image in its current image cycle
    # AND unused audio in its current audio cycle. Second priority relaxes one
    # cycle constraint, but NEVER repeats a pair while unused pairs remain.
    candidates = []
    for img in image_names:
        img_fresh = img not in ic["used"]
        for aud in audio_names:
            if f"{img}|||{aud}" in used_pairs:
                continue
            aud_fresh = aud not in ac["used"]
            score = (2 if img_fresh else 0) + (2 if aud_fresh else 0)
            candidates.append((score, random.random(), img, aud))

    if not candidates:
        state["used_pairs"] = []
        used_pairs = set()
        candidates = [(0, random.random(), i, a) for i in image_names for a in audio_names]

    candidates.sort(reverse=True)
    _, _, image, audio = candidates[0]
    pair_key = f"{image}|||{audio}"

    ic["used"].append(image)
    ac["used"].append(audio)
    state["used_pairs"].append(pair_key)
    state["last_selection"] = {
        "image": image,
        "audio": audio,
        "utc": datetime.now(timezone.utc).isoformat()
    }
    state["history"].append(state["last_selection"])
    state["history"] = state["history"][-200:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return image, audio, state
