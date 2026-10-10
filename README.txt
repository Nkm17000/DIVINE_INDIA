DIVINE_INDIA — Profile URLs at config level

Changed:
- src/publish.py
- config/social_accounts.example.json
- tests/test_rotation_and_caption_rules.py

Profile URLs now live in config/social_accounts.json, not GitHub secrets.
Credentials (page/account IDs and access tokens) remain GitHub secrets.

For each platform account entry, use:
{
  "folders": ["hanumanji"],
  "profile_url": "https://www.facebook.com/YOUR_PAGE"
}

For Instagram, use your Instagram profile URL instead. Copy the example file to
config/social_accounts.json or merge the `profile_url` property and `folders` array
into your existing account entries. Replace placeholder URLs with the actual public URLs.

Legacy array-only entries remain accepted for backward compatibility, but should be
converted to objects to configure a profile URL.

Validation:
- Existing media rotation and caption tests plus the new config-level URL test.
- Python compilation.
- Real social publishing was not run.
