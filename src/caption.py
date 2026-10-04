import random
from .config import CAPTION_PREFIX

CAPTIONS = [
    "🙏 जय श्री श्याम 🙏\n🦚 जय श्री कृष्ण 🦚\n🌸 Have a great day! 🌸\n\n#JaiShreeShyam #JaiShreeKrishna #KhatuShyam #Krishna #Bhakti",
    "🙏 जय श्री श्याम\n🦚 जय श्री कृष्ण\n✨ May your day be blessed and beautiful! ✨\n\n#JaiShreeShyam #JaiShreeKrishna #Bhakti #Devotional",
    "🌺 जय श्री श्याम 🌺\n🦚 जय श्री कृष्ण 🦚\n☀️ Have a great day filled with peace and blessings!\n\n#KhatuShyam #Krishna #RadhaKrishna #JaiShreeShyam"
]

def make_caption():
    base = random.choice(CAPTIONS)
    return f"{CAPTION_PREFIX.strip()}\n\n{base}".strip() if CAPTION_PREFIX.strip() else base
