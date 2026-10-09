"""Regression tests for strict image/ringtone deity-folder matching."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import main as reel_main

class SameFolderTests(unittest.TestCase):
    def test_hanuman_image_and_hanuman_audio_allowed(self):
        image = reel_main.IMAGE_ROOT / "hanumanji" / "example.jpg"
        ring = reel_main.RING_ROOT / "hanumanji" / "example.mp3"
        self.assertEqual(reel_main.assert_same_deity_folder(image, ring), "hanumanji")

    def test_krishna_image_and_krishna_audio_allowed(self):
        image = reel_main.IMAGE_ROOT / "shreekrishna" / "example.png"
        ring = reel_main.RING_ROOT / "shreekrishna" / "Krishna-Flute-Background-Music-Bansuri.mp3"
        self.assertEqual(reel_main.assert_same_deity_folder(image, ring), "shreekrishna")

    def test_cross_deity_pair_is_blocked(self):
        image = reel_main.IMAGE_ROOT / "shreekrishna" / "example.png"
        ring = reel_main.RING_ROOT / "hanumanji" / "example.mp3"
        with self.assertRaisesRegex(RuntimeError, "MEDIA MISMATCH BLOCKED"):
            reel_main.assert_same_deity_folder(image, ring)

if __name__ == "__main__":
    unittest.main(verbosity=2)
