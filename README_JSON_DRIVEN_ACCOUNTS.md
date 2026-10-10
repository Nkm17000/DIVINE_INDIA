# JSON-driven account publishing (up to 10 accounts per platform)

The workflow builds Facebook and Instagram publishing matrices from `config/social_accounts.json`. The publishing script resolves the token pair from each account key. Accounts 1–10 are pre-wired in `.github/workflows/daily-reel.yml`, so for account numbers 1 through 10 you can add/remove account entries in JSON without editing Python or YAML again.

## Naming convention

- Facebook: `FB_PAGE_KEY`, `FB_PAGE_KEY_2` ... `FB_PAGE_KEY_10`; matching tokens: `FB_PAGE_TOKEN`, `FB_PAGE_TOKEN_2` ... `FB_PAGE_TOKEN_10`.
- Instagram: `INSTA_PAGE_KEY`, `INSTA_PAGE_KEY_2` ... `INSTA_PAGE_KEY_10`; matching tokens: `INSTA_PAGE_TOKEN`, `INSTA_PAGE_TOKEN_2` ... `INSTA_PAGE_TOKEN_10`.
- The JSON object key must exactly match the ID secret name. `folders` entries may use `{ "name": "hanumanji", "count": 2 }`.
- The corresponding GitHub repository secrets must exist and contain valid IDs/tokens. Never put token values in the JSON file.

## Adding another account

1. Add the matching ID secret and token secret in GitHub Actions repository secrets.
2. Add an account object under `facebook` or `instagram` in `config/social_accounts.json`, using the exact ID secret name as the object key.
3. Commit and run the workflow. No code changes are required for account numbers 1–10.

## Limit

GitHub Actions does not allow dynamic lookup of a secret by a name stored in JSON. This workflow therefore explicitly exposes secret pairs 1–10. To go beyond 10 accounts per platform, extend the workflow secret environment mappings once (or change to a single encrypted JSON secret design).

The same folder counts are applied independently to every account. For example, `hanumanji` count 2 schedules two generated videos to each configured account, if two generated videos exist in that folder.
