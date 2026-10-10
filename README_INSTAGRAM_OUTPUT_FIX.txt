DIVINE INDIA — Instagram account-check output fix

Replace these two files at the repository root:
  src/publish.py
  .github/workflows/daily-reel.yml

Fixes:
- `has-instagram` inspects Instagram mappings only; it no longer loads/logs Facebook accounts.
- Diagnostic messages go to stderr for the account check.
- The workflow captures command output to a log file and appends only the valid
  `has_instagram=true` or `has_instagram=false` assignment to $GITHUB_OUTPUT.
- Facebook and Instagram remain parallel jobs in the same workflow.

After replacing, commit and push both files, then run the workflow manually.
