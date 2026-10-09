import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import main

class RotationRuleTests(unittest.TestCase):
    def test_excludes_first_and_last_ten_in_sorted_order(self):
        items = [Path(f'{i:02}.jpg') for i in range(30)]
        self.assertEqual([p.name for p in main.eligible_media(items)], [f'{i:02}.jpg' for i in range(10, 20)])

    def test_insufficient_media_falls_back_to_all_files(self):
        items = [Path(f'{i:02}.jpg') for i in range(20)]
        self.assertEqual(main.eligible_media(items), items)

    def test_edge_exclusion_still_applies_when_enough_media(self):
        items = [Path(f'{i:02}.jpg') for i in range(25)]
        self.assertEqual([p.name for p in main.eligible_media(items)], [f'{i:02}.jpg' for i in range(10, 15)])

    def test_pair_is_not_reused_before_exhaustion(self):
        # Exercise the pair selector with temporary patched roots and enough files.
        old_image_root, old_ring_root, old_root = main.IMAGE_ROOT, main.RING_ROOT, main.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td); image_root = root / 'images'; ring_root = root / 'rings'
                (image_root / 'god').mkdir(parents=True); (ring_root / 'god').mkdir(parents=True)
                images = [] ; rings = []
                for i in range(22):
                    p = image_root / 'god' / f'{i:02}.jpg'; p.touch(); images.append(p)
                    q = ring_root / 'god' / f'{i:02}.mp3'; q.touch(); rings.append(q)
                main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = image_root, ring_root, root
                state = {'folders': {}}
                first = main.choose_pair('god', images, rings, state)
                second = main.choose_pair('god', images, rings, state)
                self.assertNotEqual((first[0], first[1]), (second[0], second[1]))
        finally:
            main.IMAGE_ROOT, main.RING_ROOT, main.ROOT = old_image_root, old_ring_root, old_root

if __name__ == '__main__':
    unittest.main(verbosity=2)
