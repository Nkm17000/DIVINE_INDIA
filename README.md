# Divine India Daily Devotional Reel

The workflow automatically creates a moving 9:16 devotional reel from one image and one ringtone.

## Animation

The same image is reused across five animated segments:
1. slow zoom in + drift
2. slow zoom out
3. left-to-right pan
4. right-to-left pan
5. diagonal drift + zoom

The effect order changes on each run.

## Media folders

The code supports the existing repository layout:

- `images/`
- `audio/`

It also supports:

- `assets/images/`
- `assets/ringtones/`

## Schedule

- Manual `workflow_dispatch`
- Push to `main`
- Daily at 5:00 AM IST (`30 23 * * *` UTC)

## Video artifact

Every generated MP4 is uploaded to GitHub Actions Artifacts for 7 days, regardless of publishing results.

## Facebook

Set these GitHub Secrets if Facebook publishing is wanted:

- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN`

If missing, Facebook is skipped and video generation continues.

## Instagram — fully automatic URL

Set only:

- `IG_USER_ID`
- `IG_ACCESS_TOKEN`

You do **not** need to set `INSTAGRAM_VIDEO_URL`.

When Instagram credentials exist, the workflow automatically:
1. creates the MP4;
2. uploads it to a temporary public GitHub Release asset;
3. obtains its public HTTPS download URL;
4. sends that URL to the Instagram Graph API;
5. waits for Instagram processing;
6. publishes the Reel;
7. deletes the temporary GitHub Release and tag.

The repository must be **public** for Instagram to fetch the GitHub release asset without authentication.

No R2 setup is required.

## Required permissions

The workflow uses:

```yaml
permissions:
  contents: write
```

so its built-in GitHub token can create/delete the temporary release asset.


### 30-second animation
The same image is continuously animated through 8 subtle motion phases of about 3.75 seconds each. Effects are shuffled per reel. No fade-to-black or blank transition frames.
