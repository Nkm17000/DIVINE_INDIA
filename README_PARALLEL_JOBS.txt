DIVINE INDIA — PARALLEL FACEBOOK AND INSTAGRAM JOBS

Changed file:
  .github/workflows/daily-reel.yml

What changed:
- Keeps a single GitHub Actions workflow.
- Generates reels once in the `generate` job.
- Uploads generated reels as one artifact.
- Runs `publish-facebook` and `publish-instagram` as sibling jobs in parallel.
- Both publishing jobs depend only on `generate`; neither depends on the other.
- A Facebook publishing failure therefore cannot cancel or block the Instagram publishing job, and vice versa.
- Rotation history is committed by the generation job, independently of publishing results.
- Keeps push, manual, and 6 AM / 6 PM IST scheduled triggers.

Apply:
1. Replace `.github/workflows/daily-reel.yml` with the file in this ZIP.
2. Keep your existing `src/`, `config/`, `requirements.txt`, `images/`, and `rings/` files.
3. Commit and push the workflow change.

Important:
- The Instagram job uses temporary GitHub Release assets as public video URLs, as in the existing workflow. The repository must be public for that method to work.
- Verify that `contents: write` is allowed in repository Actions settings so the rotation-state commit can be pushed.
