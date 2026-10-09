import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import main


class RotationRuleTests(unittest.TestCase):
    def test_all_media_files_remain_eligible(self):
        items = [Path(f"{i:02}.jpg") for i in range(22)]
        self.assertEqual(main.eligible_media(items), items)

    def test_excludes_images_and_ringtones_used_in_last_five_selections(self):
        old_image_root, old_ring_root, old_root = main.IMAGE_ROOT, main.RING_ROOT, main.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                image_root = root / "images"
                ring_root = root / "rings"
                (image_root / "god").mkdir(parents=True)
                (ring_root / "god").mkdir(parents=True)
                images, rings = [], []
                for i in range(12):
                    p = image_root / "god" / f"{i:02}.jpg"
                    q = ring_root / "god" / f"{i:02}.mp3"
                    p.touch(); q.touch()
                    images.append(p); rings.append(q)
                main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = image_root, ring_root, root
                history = [
                    {"image": f"god/{i:02}.jpg", "ring": f"god/{i:02}.mp3"}
                    for i in range(5)
                ]
                recent_image_names = {x["image"] for x in history}
                recent_ring_names = {x["ring"] for x in history}
                state = {"folders": {"god": {"history": history, "used_pairs": [
                    f"god/{i:02}.jpg|||god/{i:02}.mp3" for i in range(5)
                ], "cycle": 0}}}
                image, ring, _ = main.choose_pair("god", images, rings, state)
                self.assertNotIn(image.relative_to(image_root).as_posix(),
                                 recent_image_names)
                self.assertNotIn(ring.relative_to(ring_root).as_posix(),
                                 recent_ring_names)
        finally:
            main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = old_image_root, old_ring_root, old_root

    def test_same_image_cannot_repeat_with_a_different_tone_within_recent_window(self):
        old_image_root, old_ring_root, old_root = main.IMAGE_ROOT, main.RING_ROOT, main.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                image_root = root / "images"
                ring_root = root / "rings"
                (image_root / "god").mkdir(parents=True)
                (ring_root / "god").mkdir(parents=True)
                images = []
                rings = []
                for i in range(8):
                    p = image_root / "god" / f"{i:02}.jpg"; p.touch(); images.append(p)
                    q = ring_root / "god" / f"{i:02}.mp3"; q.touch(); rings.append(q)
                main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = image_root, ring_root, root
                state = {"folders": {}}
                first_image, first_ring, _ = main.choose_pair("god", images, rings, state)
                for _ in range(5):
                    image, ring, _ = main.choose_pair("god", images, rings, state)
                    self.assertNotEqual(image, first_image)
                    self.assertNotEqual(ring, first_ring)
        finally:
            main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = old_image_root, old_ring_root, old_root


if __name__ == "__main__":
    unittest.main(verbosity=2)
