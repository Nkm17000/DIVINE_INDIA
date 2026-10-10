# Divine India — shared generation, parallel publishing, and media history

## Files to replace/add

Replace:
- `.github/workflows/daily-reel.yml`
- `src/publish.py`

Add:
- `src/update_history.py`

## Workflow behavior

1. `Generate reels once` runs first and generates each configured deity/video only once.
2. The same generated artifact is shared with Facebook and Instagram publishing jobs.
3. GitHub Actions shows one matrix job per generated video under each platform. Each platform matrix allows **3 concurrent videos** (`max-parallel: 3`); when one finishes, GitHub can start the next queued video.
4. A Facebook failure does not cancel Instagram or other matrix jobs (`fail-fast: false`). A failed account is recorded while other configured accounts for that video are still attempted.
5. Instagram prepares public Release-asset URLs once, then its matrix jobs publish up to 3 videos concurrently. The temporary release is removed after the Instagram matrix finishes.
6. One final history job combines generation selections and publication results, then updates `data/history/publication_history.csv` and `state/rotation_state.json` in a single commit/push attempt sequence.

## History table

`data/history/publication_history.csv` has a `GENERATION` row for every generated video, including image and ringtone paths, plus one result row per platform/account with `PUBLISHED`, `FAILED`, or `SKIPPED`, post ID, timestamp, and error.

## Requirements / notes

- Keep your existing `config/social_accounts.json` and GitHub Secrets (`FB_PAGE_KEY`, `FB_PAGE_TOKEN`, numbered variants, and Instagram equivalents).
- The Instagram workflow continues to require a **public GitHub repository** for temporary public video URLs, as in the prior workflow design.
- `max-parallel: 3` is set independently for Facebook and Instagram, so up to 3 Facebook video jobs and 3 Instagram video jobs can run at once.
- This package contains only the changed/new files, not your large media directories.
