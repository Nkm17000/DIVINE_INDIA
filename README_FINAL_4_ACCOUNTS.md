# DIVINE_INDIA — four-account publishing update

## Files to replace/add

Replace these files in your repository:
- `.github/workflows/daily-reel.yml`
- `src/publish.py`
- `src/update_history.py`

Add/merge this account mapping file:
- `config/social_accounts.json`

If your existing `config/social_accounts.json` contains other settings you need, merge the four account mappings into it instead of overwriting unrelated settings.

## GitHub Actions secrets used

Facebook account 1: `FB_PAGE_KEY`, `FB_PAGE_TOKEN`
Facebook account 2: `FB_PAGE_KEY_2`, `FB_PAGE_TOKEN_2`
Instagram account 1: `INSTA_PAGE_KEY`, `INSTA_PAGE_TOKEN`
Instagram account 2: `INSTA_PAGE_KEY_2`, `INSTA_PAGE_TOKEN_2`

The workflow passes numbered account secrets through to the publish jobs. The account mapping must include the corresponding `*_KEY` name for each account to be published. The `*_KEY` value must be the platform's correct page/account ID, and its paired `*_TOKEN` must belong to that same account.

## Behavior

- Reels are generated once and shared between publishing jobs.
- Each generated video is attempted against both configured Facebook pages and both configured Instagram accounts for each folder.
- Facebook and Instagram publish independently. Each platform matrix allows up to three video jobs concurrently (`max-parallel: 3`).
- A publishing failure for one account is recorded and does not prevent the script from attempting the other configured account for that video.
- Final history records image/ringtone selection and each destination's publishing status, post ID, timestamp, and error.
- Instagram uses temporary public GitHub Release asset URLs; the existing workflow requires a public GitHub repository for this mechanism.

## Important

This code cannot bypass Meta restrictions. Facebook Graph API error `368` is a platform rate-limit/spam-prevention block and may continue even when account mapping is correct. Wait before retrying; do not repeatedly rerun failed publishing jobs. Tokens/IDs are not included in this ZIP.
