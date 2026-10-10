import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import main
import publish


class RotationRuleTests(unittest.TestCase):
    def setUp(self):
        self.old_roots = main.IMAGE_ROOT, main.RING_ROOT, main.ROOT

    def tearDown(self):
        main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = self.old_roots

    def test_every_pair_once_then_cycle_resets_and_last_ten_media_never_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_root, ring_root = root / "images", root / "rings"
            (image_root / "god").mkdir(parents=True)
            (ring_root / "god").mkdir(parents=True)
            images, rings = [], []
            for i in range(20):
                image = image_root / "god" / f"{i:02}.jpg"
                image.touch()
                images.append(image)
                ring = ring_root / "god" / f"{i:02}.mp3"
                ring.touch()
                rings.append(ring)
            main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = image_root, ring_root, root
            state = {"schema_version": 3, "folders": {}}
            total_pairs = len(images) * len(rings)
            first_cycle_pairs = set()
            history_images, history_rings = [], []
            for _ in range(total_pairs):
                image, ring, selection = main.choose_pair("god", images, rings, state)
                image_key = image.relative_to(image_root).as_posix()
                ring_key = ring.relative_to(ring_root).as_posix()
                pair = f"{image_key}|||{ring_key}"
                self.assertNotIn(pair, first_cycle_pairs)
                self.assertNotIn(image_key, history_images[-10:])
                self.assertNotIn(ring_key, history_rings[-10:])
                first_cycle_pairs.add(pair)
                history_images.append(image_key)
                history_rings.append(ring_key)
            self.assertEqual(len(first_cycle_pairs), total_pairs)
            self.assertEqual(len(state["folders"]["god"]["used_pairs"]), total_pairs)
            image, ring, selection = main.choose_pair("god", images, rings, state)
            self.assertEqual(selection["cycle"], 1)
            self.assertNotIn(image.relative_to(image_root).as_posix(), history_images[-10:])
            self.assertNotIn(ring.relative_to(ring_root).as_posix(), history_rings[-10:])

    def test_rejects_fewer_than_twenty_ringtones_for_strict_cycle_rule(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_root, ring_root = root / "images", root / "rings"
            (image_root / "god").mkdir(parents=True)
            (ring_root / "god").mkdir(parents=True)
            images, rings = [], []
            for i in range(20):
                image = image_root / "god" / f"{i:02}.jpg"
                image.touch()
                images.append(image)
            for i in range(19):
                ring = ring_root / "god" / f"{i:02}.mp3"
                ring.touch()
                rings.append(ring)
            main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = image_root, ring_root, root
            with self.assertRaisesRegex(RuntimeError, "At least 20 distinct ringtones"):
                main.choose_pair("god", images, rings, {"folders": {}})

    def test_platform_specific_like_follow_urls(self):
        fb = publish.platform_caption("🙏 Jai Bajrangbali", "facebook",
                                      {"profile_url": "https://facebook.com/example"})
        ig = publish.platform_caption("🙏 Jai Bajrangbali", "instagram",
                                      {"profile_url": "https://instagram.com/example"})
        self.assertIn("Please like and follow our Facebook Page.", fb)
        self.assertIn("https://facebook.com/example", fb)
        self.assertIn("Please like and follow us on Instagram.", ig)
        self.assertIn("https://instagram.com/example", ig)


if __name__ == "__main__":
    unittest.main(verbosity=2)
