#!/usr/bin/env python3
"""Publish each folder's reel to accounts mapped in config/social_accounts.json.

JSON maps secret *key names* to folder names. Credentials are read from environment
variables populated by GitHub Actions secrets; no tokens belong in the JSON file.
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "output"
GRAPH = os.getenv("META_GRAPH_VERSION", "v24.0")


def _paired_token_name(key_name: str, platform: str) -> str:
    """FB_PAGE_KEY[_N] -> FB_PAGE_TOKEN[_N], INSTA_PAGE_KEY[_N] -> INSTA_PAGE_TOKEN[_N]."""
    prefix = "FB_PAGE" if platform == "facebook" else "INSTA_PAGE"
    match = re.fullmatch(re.escape(prefix) + r"_KEY(_\d+)?", key_name)
    if not match:
        raise ValueError(f"Invalid {platform} account key '{key_name}'. Expected {prefix}_KEY or {prefix}_KEY_2, etc.")
    return f"{prefix}_TOKEN{match.group(1) or ''}"


def platform_caption(caption: str, platform: str, account: dict) -> str:
    """Add platform-specific profile URL and like/follow call to action."""
    url = str(account.get("profile_url", "")).strip()
    if platform == "facebook":
        cta = "Please like and follow our Facebook Page."
        label = "Facebook Page"
    else:
        cta = "Please like and follow us on Instagram."
        label = "Instagram"
    if url:
        cta += f"\n{label}: {url}"
    else:
        print(
            f"WARNING: no profile URL configured for {platform} account "
            f"{account.get('account_key', 'unknown')}; add profile_url in config/social_accounts.json."
        )
    return f"{caption.rstrip()}\n\n{cta}"


def load_accounts() -> dict:
    """Resolve shared account credentials and assign each account only to configured folders."""
    config_path = ROOT / "config" / "social_accounts.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing account config: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("config/social_accounts.json must be an object with facebook and instagram mappings.")

    resolved: dict[str, dict[str, list[dict]]] = {}
    for platform in ("facebook", "instagram"):
        mappings = data.get(platform, {})
        if not isinstance(mappings, dict):
            raise RuntimeError(f"The '{platform}' value in config/social_accounts.json must be an object mapping secret key names to folder arrays.")
        for key_env, account_config in mappings.items():
            if not isinstance(key_env, str):
                raise RuntimeError(f"Invalid account key name in {platform} mapping: {key_env!r}")
            # Public profile URLs are configuration, not credentials/secrets.
            # Preferred format: {"folders": ["hanumanji"], "profile_url": "https://..."}
            # Legacy list format remains supported for backward compatibility.
            if isinstance(account_config, list):
                folders = account_config
                profile_url = ""
            elif isinstance(account_config, dict):
                folders = account_config.get("folders", [])
                profile_url = str(account_config.get("profile_url", "")).strip()
            else:
                raise RuntimeError(
                    f"{platform}.{key_env} must be an object with 'folders' and 'profile_url' "
                    "or a legacy array of folder names."
                )
            if not isinstance(folders, list) or not all(isinstance(folder, str) and folder.strip() for folder in folders):
                raise RuntimeError(f"{platform}.{key_env}.folders must contain a JSON array of non-empty folder names.")
            if profile_url and not profile_url.startswith(("https://", "http://")):
                raise RuntimeError(f"{platform}.{key_env}.profile_url must start with https:// or http://.")
            token_env = _paired_token_name(key_env, platform)
            account_id = os.getenv(key_env, "").strip()
            token = os.getenv(token_env, "").strip()
            if not account_id and not token:
                print(f"INFO: {platform} account '{key_env}' skipped (GitHub secrets not configured).")
                continue
            if not account_id or not token:
                print(f"WARNING: incomplete {platform} credentials: configure both {key_env} and {token_env} in GitHub Secrets.")
                continue
            for folder in dict.fromkeys(folder.strip() for folder in folders):
                resolved.setdefault(folder, {"facebook": [], "instagram": []})
                if platform == "facebook":
                    resolved[folder][platform].append({
                        "page_id": account_id, "access_token": token, "account_key": key_env,
                        "profile_url": profile_url,
                    })
                else:
                    resolved[folder][platform].append({
                        "user_id": account_id, "access_token": token, "account_key": key_env,
                        "profile_url": profile_url,
                    })
    return resolved


def instagram_urls() -> dict:
    raw = os.getenv("INSTAGRAM_VIDEO_URLS_JSON", "{}").strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"INSTAGRAM_VIDEO_URLS_JSON is invalid JSON: {exc}") from exc
    return value if isinstance(value, dict) else {}


def post_facebook(video: Path, caption: str, account: dict, folder: str) -> None:
    page_id, token = str(account.get("page_id", "")).strip(), str(account.get("access_token", "")).strip()
    if not page_id or not token:
        print(f"Facebook account skipped for {folder}: missing page_id/access_token")
        return
    with video.open("rb") as f:
        r = requests.post(f"https://graph.facebook.com/{GRAPH}/{page_id}/videos",
                          params={"access_token": token, "description": caption},
                          files={"source": (video.name, f, "video/mp4")}, timeout=300)
    if not r.ok:
        raise RuntimeError(f"Facebook publish failed for {folder}/Page {page_id}: HTTP {r.status_code}: {r.text}")
    print(f"Facebook published [{folder}] account key {account.get('account_key', '')}, Page {page_id}: {r.json()}")


def post_instagram(video_url: str, caption: str, account: dict, folder: str) -> None:
    user_id, token = str(account.get("user_id", "")).strip(), str(account.get("access_token", "")).strip()
    if not user_id or not token:
        print(f"Instagram account skipped for {folder}: missing user_id/access_token")
        return
    if not video_url:
        raise RuntimeError(f"No public video URL for Instagram folder '{folder}'. Check workflow release setup.")
    r = requests.post(f"https://graph.facebook.com/{GRAPH}/{user_id}/media",
                      data={"media_type": "REELS", "video_url": video_url,
                            "caption": caption, "access_token": token}, timeout=120)
    if not r.ok:
        raise RuntimeError(f"Instagram container failed for {folder}/{user_id}: HTTP {r.status_code}: {r.text}")
    creation_id = r.json().get("id")
    if not creation_id:
        raise RuntimeError(f"Instagram returned no creation ID for {folder}/{user_id}: {r.text}")
    for attempt in range(36):
        time.sleep(5)
        status_response = requests.get(f"https://graph.facebook.com/{GRAPH}/{creation_id}",
                                       params={"fields": "status_code,status", "access_token": token}, timeout=60)
        if not status_response.ok:
            raise RuntimeError(f"Instagram status check failed: HTTP {status_response.status_code}: {status_response.text}")
        status = status_response.json().get("status_code")
        print(f"Instagram processing [{folder}/{user_id}] {attempt + 1}/36: {status}")
        if status == "FINISHED":
            break
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram processing failed for {folder}/{user_id}: {status_response.text}")
    else:
        raise RuntimeError(f"Instagram processing timed out for {folder}/{user_id}")
    publish = requests.post(f"https://graph.facebook.com/{GRAPH}/{user_id}/media_publish",
                            data={"creation_id": creation_id, "access_token": token}, timeout=120)
    if not publish.ok:
        raise RuntimeError(f"Instagram publish failed for {folder}/{user_id}: HTTP {publish.status_code}: {publish.text}")
    print(f"Instagram published [{folder}] account key {account.get('account_key', '')}, account {user_id}: {publish.json()}")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1].lower() not in {"facebook", "instagram", "all", "has-instagram"}:
        raise SystemExit("Usage: python src/publish.py facebook|instagram|all|has-instagram")
    target = sys.argv[1].lower()
    accounts = load_accounts()
    if target == "has-instagram":
        print("has_instagram=" + str(any(v.get("instagram") for v in accounts.values())).lower())
        return
    urls = instagram_urls()
    errors = []
    for folder_dir in sorted(p for p in OUT_ROOT.iterdir() if p.is_dir()):
        folder = folder_dir.name
        video = folder_dir / "daily_reel.mp4"
        caption_file = folder_dir / "caption.txt"
        if not video.is_file() or not caption_file.is_file():
            continue
        caption = caption_file.read_text(encoding="utf-8").strip()
        configured = accounts.get(folder, {"facebook": [], "instagram": []})
        platforms = ("facebook", "instagram") if target == "all" else (target,)
        for platform in platforms:
            if platform == "has-instagram":
                continue
            for account in configured.get(platform, []):
                try:
                    caption_for_platform = platform_caption(caption, platform, account)
                    if platform == "facebook":
                        post_facebook(video, caption_for_platform, account, folder)
                    else:
                        post_instagram(str(urls.get(folder, "")), caption_for_platform, account, folder)
                except Exception as exc:
                    errors.append(f"{platform} [{folder}] [{account.get('account_key', 'unknown')}]: {exc}")
                    print(f"ERROR: {errors[-1]}")
    if errors:
        raise RuntimeError("One or more publishing targets failed:\n" + "\n".join(errors))


if __name__ == "__main__":
    main()
