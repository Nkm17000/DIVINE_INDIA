DIVINE_INDIA orientation validation fix

Replace:
  src/main.py

Cause:
  verify_video() hard-coded portrait dimensions (1080x1920), but video.py intentionally
  renders landscape source images as 1920x1080. FFmpeg succeeded; post-render validation
  incorrectly rejected the valid horizontal video.

Fix:
  main.py now passes the width and height returned by create_video() to verify_video().
  It validates both orientations without disabling verification.

Validation performed:
  Python compilation succeeded for all Python files in the supplied src folder.

Expected behavior:
  Portrait source -> 1080x1920
  Landscape source -> 1920x1080
