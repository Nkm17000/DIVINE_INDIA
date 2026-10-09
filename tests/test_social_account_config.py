"""Tests for shared account credentials mapped to multiple deity folders."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import publish


class SocialAccountConfigTests(unittest.TestCase):
    def test_one_account_can_be_mapped_to_multiple_folders(self):
        config_path = ROOT / "config" / "social_accounts.json"
        original = config_path.read_text(encoding="utf-8")
        try:
            config_path.write_text(json.dumps({
                "facebook": {"FB_PAGE_KEY": ["hanumanji", "shreekrishna"]},
                "instagram": {"INSTA_PAGE_KEY": ["shyambaba"]}
            }), encoding="utf-8")
            with patch.dict(os.environ, {
                "FB_PAGE_KEY": "fb-id", "FB_PAGE_TOKEN": "fb-token",
                "INSTA_PAGE_KEY": "ig-id", "INSTA_PAGE_TOKEN": "ig-token"
            }, clear=False):
                accounts = publish.load_accounts()
            self.assertEqual(accounts["hanumanji"]["facebook"][0]["page_id"], "fb-id")
            self.assertEqual(accounts["shreekrishna"]["facebook"][0]["access_token"], "fb-token")
            self.assertEqual(accounts["shyambaba"]["instagram"][0]["user_id"], "ig-id")
        finally:
            config_path.write_text(original, encoding="utf-8")

    def test_second_account_pairs_key_and_token_suffix(self):
        config_path = ROOT / "config" / "social_accounts.json"
        original = config_path.read_text(encoding="utf-8")
        try:
            config_path.write_text(json.dumps({
                "facebook": {"FB_PAGE_KEY_2": ["hanumanji"]},
                "instagram": {"INSTA_PAGE_KEY_2": ["shreekrishna"]}
            }), encoding="utf-8")
            with patch.dict(os.environ, {
                "FB_PAGE_KEY_2": "fb-id-2", "FB_PAGE_TOKEN_2": "fb-token-2",
                "INSTA_PAGE_KEY_2": "ig-id-2", "INSTA_PAGE_TOKEN_2": "ig-token-2"
            }, clear=False):
                accounts = publish.load_accounts()
            self.assertEqual(accounts["hanumanji"]["facebook"][0]["access_token"], "fb-token-2")
            self.assertEqual(accounts["shreekrishna"]["instagram"][0]["user_id"], "ig-id-2")
        finally:
            config_path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
