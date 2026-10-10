import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, call

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import publish


class MultiVideoPublishingTests(unittest.TestCase):
    def test_facebook_publishes_each_video_in_folder(self):
        old_root, old_out, old_argv = publish.ROOT, publish.OUT_ROOT, sys.argv
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td); out = root / 'output' / 'hanumanji'; out.mkdir(parents=True)
                (out / 'daily_reel.mp4').write_bytes(b'video1')
                (out / 'daily_reel_2.mp4').write_bytes(b'video2')
                (out / 'caption.txt').write_text('caption', encoding='utf-8')
                publish.ROOT, publish.OUT_ROOT = root, root / 'output'
                sys.argv = ['publish.py', 'facebook']
                accounts = {'hanumanji': {'facebook': [{'page_id':'id','access_token':'token','account_key':'FB_PAGE_KEY','profile_url':''}], 'instagram': []}}
                with patch.object(publish, 'load_accounts', return_value=accounts), \
                     patch.object(publish, 'post_facebook') as post:
                    publish.main()
                self.assertEqual(post.call_count, 2)
                self.assertEqual({c.args[0].name for c in post.call_args_list}, {'daily_reel.mp4','daily_reel_2.mp4'})
        finally:
            publish.ROOT, publish.OUT_ROOT, sys.argv = old_root, old_out, old_argv

    def test_instagram_uses_per_video_public_urls(self):
        old_root, old_out, old_argv = publish.ROOT, publish.OUT_ROOT, sys.argv
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td); out = root / 'output' / 'hanumanji'; out.mkdir(parents=True)
                (out / 'daily_reel.mp4').write_bytes(b'video1')
                (out / 'daily_reel_2.mp4').write_bytes(b'video2')
                (out / 'caption.txt').write_text('caption', encoding='utf-8')
                publish.ROOT, publish.OUT_ROOT = root, root / 'output'
                sys.argv = ['publish.py', 'instagram']
                accounts = {'hanumanji': {'facebook': [], 'instagram': [{'user_id':'id','access_token':'token','account_key':'INSTA_PAGE_KEY','profile_url':''}]}}
                urls = {'hanumanji/daily_reel.mp4':'https://example.com/one.mp4',
                        'hanumanji/daily_reel_2.mp4':'https://example.com/two.mp4'}
                with patch.object(publish, 'load_accounts', return_value=accounts), \
                     patch.object(publish, 'instagram_urls', return_value=urls), \
                     patch.object(publish, 'post_instagram') as post:
                    publish.main()
                self.assertEqual(post.call_count, 2)
                self.assertEqual({c.args[0] for c in post.call_args_list}, set(urls.values()))
        finally:
            publish.ROOT, publish.OUT_ROOT, sys.argv = old_root, old_out, old_argv


if __name__ == '__main__':
    unittest.main(verbosity=2)
