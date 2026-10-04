from .config import CAPTION_PREFIX

CAPTIONS = [
    "🙏 राधे राधे 🙏\n🦚 जय श्री कृष्ण 🦚\n🌸 जय श्री श्याम 🌸\n\n#RadheRadhe #JaiShreeKrishna #JaiShreeShyam #KhatuShyam #Bhakti",
    "🌺 राधे राधे 🌺\n🙏 जय श्री कृष्ण 🙏\n🪷 जय श्री श्याम 🪷\n\n#RadheRadhe #JaiShreeKrishna #JaiShreeShyam #Krishna #Bhakti",
    "🦚 जय श्री कृष्ण 🦚\n🌸 राधे राधे 🌸\n🙏 जय श्री श्याम 🙏\n\n#JaiShreeKrishna #RadheRadhe #JaiShreeShyam #Devotional #Bhakti",
    "🙏 जय श्री श्याम 🙏\n🌺 राधे राधे 🌺\n🦚 जय श्री कृष्ण 🦚\n\n#JaiShreeShyam #RadheRadhe #JaiShreeKrishna #KhatuShyam #Bhakti",
]

def make_caption():
    # No Good Morning / Good Evening text. Keep every caption devotional.
    base = CAPTIONS[0] if len(CAPTIONS) == 1 else __import__('random').choice(CAPTIONS)
    return f"{CAPTION_PREFIX.strip()}\n\n{base}".strip() if CAPTION_PREFIX.strip() else base
