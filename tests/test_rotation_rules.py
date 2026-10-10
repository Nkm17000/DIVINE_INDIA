import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import main


class RotationRuleTests(unittest.TestCase):
    def test_eligible_media_keeps_all_files_for_history_based_rotation(self):
        items = [Path(f'{i:02}.jpg') for i in range(30)]
        self.assertEqual(main.eligible_media(items), items)

    def test_rotation_fallback_always_selects_when_only_one_image_and_ring(self):
        old_image_root, old_ring_root, old_root = main.IMAGE_ROOT, main.RING_ROOT, main.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                image_root, ring_root = root / 'images', root / 'rings'
                (image_root / 'god').mkdir(parents=True)
                (ring_root / 'god').mkdir(parents=True)
                image = image_root / 'god' / 'only.jpg'; image.touch()
                ring = ring_root / 'god' / 'only.mp3'; ring.touch()
                main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = image_root, ring_root, root
                state = {'folders': {}}
                selected = main.choose_pair('god', [image], [ring], state)
                self.assertEqual(selected[0], image)
                self.assertEqual(selected[1], ring)
                # A new cycle may use the only available pair again; it must not skip.
                selected2 = main.choose_pair('god', [image], [ring], state)
                self.assertEqual((selected2[0], selected2[1]), (image, ring))
        finally:
            main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = old_image_root, old_ring_root, old_root

    def test_pair_is_not_reused_before_exhaustion(self):
        old_image_root, old_ring_root, old_root = main.IMAGE_ROOT, main.RING_ROOT, main.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td); image_root = root / 'images'; ring_root = root / 'rings'
                (image_root / 'god').mkdir(parents=True); (ring_root / 'god').mkdir(parents=True)
                images, rings = [], []
                for i in range(3):
                    ip = image_root / 'god' / f'{i:02}.jpg'; ip.touch(); images.append(ip)
                    rp = ring_root / 'god' / f'{i:02}.mp3'; rp.touch(); rings.append(rp)
                main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = image_root, ring_root, root
                state = {'folders': {}}
                seen = set()
                for _ in range(9):
                    image, ring, _ = main.choose_pair('god', images, rings, state)
                    pair = (image, ring)
                    self.assertNotIn(pair, seen)
                    seen.add(pair)
                self.assertEqual(len(seen), 9)
                # After every combination has been used, the cycle resets and still returns a pair.
                image, ring, _ = main.choose_pair('god', images, rings, state)
                self.assertIn((image, ring), seen)
        finally:
            main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = old_image_root, old_ring_root, old_root

    def test_video_count_config_reads_name_count_objects(self):
        old_root = main.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                main.ROOT = Path(td)
                (main.ROOT / 'config').mkdir()
                (main.ROOT / 'config' / 'social_accounts.json').write_text(json.dumps({
                    'facebook': {'FB_PAGE_KEY': {'folders': [{'name': 'hanumanji', 'count': 2}, {'name': 'shreekrishna', 'count': 1}], 'profile_url': 'https://example.com/fb'}},
                    'instagram': {'INSTA_PAGE_KEY': {'folders': [{'name': 'hanumanji', 'count': 2}, {'name': 'shreekrishna', 'count': 1}], 'profile_url': 'https://example.com/ig'}}
                }), encoding='utf-8')
                self.assertEqual(main.load_video_counts(), {'hanumanji': 2, 'shreekrishna': 1})
        finally:
            main.ROOT = old_root


if __name__ == '__main__':
    unittest.main(verbosity=2)
