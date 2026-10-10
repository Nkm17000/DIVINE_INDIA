# Folder counts and partial-success reporting

## Folder counts
`config/social_accounts.json` now uses object entries for each folder. `count` determines how many already-generated videos from that folder are included in each account's publishing matrix. Hanumanji is set to 2; Shree Krishna, Maa Durga, and Shyam Baba are set to 1.

The generator must create the requested number of distinct MP4s in each folder (for Hanumanji, e.g. `daily_reel.mp4` and `daily_reel_2.mp4`). The workflow logs a warning if fewer videos exist than the configured count; it does not fabricate a second distinct reel by duplicating a file.

## Account jobs
Every account/video pair has its own GitHub Actions matrix job and is published using that account's matching ID/token secrets. Each platform matrix has `max-parallel: 3`.

## Final summary
The `Final publication summary` job reads per-video result artifacts and reports `SUCCESS`, `PARTIAL_SUCCESS`, or `FAILURE`, with successful, failed, skipped, and total counts plus account/folder/video/post details. Any successful post alongside a failed/skipped result is reported as `PARTIAL_SUCCESS`. It reports `FAILURE` only when no post succeeded.

## Install
Merge these files into the existing repository, preserving the rest of the project:
- `.github/workflows/daily-reel.yml`
- `config/social_accounts.json`
- `README_COUNT_AND_PARTIAL_SUCCESS.md`

The current project ZIP supplied for this update did not contain `src/main.py` or `requirements.txt`, so this patch deliberately does not replace those files. Verify your existing generator emits the configured number of reels per folder.
