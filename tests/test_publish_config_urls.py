import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import publish


class ProfileURLConfigTests(unittest.TestCase):
    def test_profile_urls_come_from_config_not_environment_secrets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir()
            (root / "config" / "social_accounts.json").write_text(json.dumps({
                "facebook": {"FB_PAGE_KEY": {
                    "folders": [{"name": "god", "count": 2}], "profile_url": "https://www.facebook.com/my-page"
                }},
                "instagram": {"INSTA_PAGE_KEY": {
                    "folders": [{"name": "god", "count": 2}], "profile_url": "https://www.instagram.com/my-profile/"
                }}
            }), encoding="utf-8")
            old_root = publish.ROOT
            keys = ("FB_PAGE_KEY", "FB_PAGE_TOKEN", "INSTA_PAGE_KEY", "INSTA_PAGE_TOKEN",
                    "FB_PAGE_URL", "INSTA_PROFILE_URL")
            old_env = {key: os.environ.get(key) for key in keys}
            try:
                publish.ROOT = root
                os.environ.update({"FB_PAGE_KEY": "123", "FB_PAGE_TOKEN": "fb-token",
                                   "INSTA_PAGE_KEY": "456", "INSTA_PAGE_TOKEN": "ig-token"})
                os.environ.pop("FB_PAGE_URL", None)
                os.environ.pop("INSTA_PROFILE_URL", None)
                accounts = publish.load_accounts()
                self.assertEqual(accounts["god"]["facebook"][0]["profile_url"],
                                 "https://www.facebook.com/my-page")
                self.assertEqual(accounts["god"]["instagram"][0]["profile_url"],
                                 "https://www.instagram.com/my-profile/")
            finally:
                publish.ROOT = old_root
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_platform_captions_include_configured_url_and_cta(self):
        fb = publish.platform_caption("Caption", "facebook",
                                      {"profile_url": "https://www.facebook.com/my-page"})
        ig = publish.platform_caption("Caption", "instagram",
                                      {"profile_url": "https://www.instagram.com/my-profile/"})
        self.assertIn("Please like and follow our Facebook Page.", fb)
        self.assertIn("https://www.facebook.com/my-page", fb)
        self.assertIn("Please like and follow us on Instagram @divineindia247.", ig)
        self.assertIn("Visit the link in our bio.", ig)
        # URL is included for visibility, but Instagram Reel caption URLs aren't clickable.
        self.assertIn("https://www.instagram.com/my-profile/", ig)


if __name__ == "__main__":
    unittest.main(verbosity=2)
