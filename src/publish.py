#!/usr/bin/env python3
"""Publish each folder's reel to accounts mapped in config/social_accounts.json.

JSON maps secret *key names* to folder names. Credentials are read from environment
variables populated by GitHub Actions secrets; no tokens belong in the JSON file.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import base64
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "output"
GRAPH = os.getenv("META_GRAPH_VERSION", "v24.0")

BLOCK_STATE_PATH = "state/facebook_daily_blocks.json"
INDIA_TZ = ZoneInfo("Asia/Kolkata")

def _india_date() -> str:
    return datetime.now(INDIA_TZ).date().isoformat()

def _github_api_url(path: str = BLOCK_STATE_PATH) -> str | None:
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    if not repo:
        return None
    return f"https://api.github.com/repos/{repo}/contents/{path}"

def _read_fb_blocks() -> tuple[dict, str | None]:
    """Read the persistent daily Facebook block list from the repository branch."""
    url = _github_api_url()
    token = os.getenv("GH_TOKEN", "").strip()
    local_path = ROOT / BLOCK_STATE_PATH
    local_data = {}
    try:
        local_data = json.loads(local_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    if not url or not token:
        return local_data if isinstance(local_data, dict) else {}, None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    try:
        response = requests.get(url, headers=headers, params={"ref": os.getenv("GITHUB_REF_NAME", "main")}, timeout=15)
        if response.status_code == 404:
            return {}, None
        response.raise_for_status()
        payload = response.json()
        content = base64.b64decode(payload.get("content", "")).decode("utf-8")
        data = json.loads(content) if content.strip() else {}
        return (data if isinstance(data, dict) else {}), payload.get("sha")
    except Exception as exc:
        print(f"WARNING: could not read persistent Facebook daily-block state; using local state: {exc}")
        return local_data if isinstance(local_data, dict) else {}, None

def _write_fb_block(account_key: str, page_id: str, error: str) -> None:
    """Persist a code-368 account block until the next India-local calendar day."""
    local_path = ROOT / BLOCK_STATE_PATH
    local_path.parent.mkdir(parents=True, exist_ok=True)
    data, _ = _read_fb_blocks()
    data.setdefault("accounts", {})[account_key] = {
        "blocked_date_ist": _india_date(),
        "page_id": page_id,
        "reason": "Meta Graph API error 368 (rate/spam prevention)",
        "message": error[:1200],
        "blocked_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    local_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    url = _github_api_url()
    token = os.getenv("GH_TOKEN", "").strip()
    if not url or not token:
        print("WARNING: GH_TOKEN/GITHUB_REPOSITORY unavailable; daily block is only local to this job.")
        return
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    branch = os.getenv("GITHUB_REF_NAME", "main")
    for attempt in range(3):
        try:
            current = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
            sha = current.json().get("sha") if current.status_code == 200 else None
            if current.status_code not in (200, 404):
                current.raise_for_status()
            # Re-read latest content before updating so concurrent 368 events are merged.
            if current.status_code == 200:
                latest = json.loads(base64.b64decode(current.json().get("content", "")).decode("utf-8") or "{}")
                if isinstance(latest, dict):
                    latest.setdefault("accounts", {}).update(data.get("accounts", {}))
                    data = latest
            body = {"message": f"chore: block Facebook account {account_key} for {_india_date()} after Meta 368",
                    "content": base64.b64encode((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()).decode(),
                    "branch": branch}
            if sha:
                body["sha"] = sha
            saved = requests.put(url, headers=headers, json=body, timeout=20)
            if saved.status_code in (200, 201):
                print(f"DAILY BLOCK SAVED: Facebook account {account_key} will be skipped for the rest of {_india_date()} IST.")
                return
            if saved.status_code not in (409, 422):
                saved.raise_for_status()
        except Exception as exc:
            print(f"WARNING: could not persist Facebook daily block (attempt {attempt + 1}/3): {exc}")
        time.sleep(attempt + 1)
    print("WARNING: failed to persist Facebook daily block after retries; check GITHUB_TOKEN permissions.")

def _facebook_account_blocked(account_key: str) -> tuple[bool, str]:
    data, _ = _read_fb_blocks()
    item = data.get("accounts", {}).get(account_key, {}) if isinstance(data, dict) else {}
    blocked = bool(item and item.get("blocked_date_ist") == _india_date())
    if blocked:
        return True, f"Account blocked for today after Meta error 368 ({item.get('blocked_date_ist')} IST)."
    return False, ""

def _is_meta_368(error: str) -> bool:
    return bool(re.search(r'(?i)(?:\"code\"\s*:\s*368|error code 368|\bcode[=: ]+368\b)', error))


def _paired_token_name(key_name: str, platform: str) -> str:
    """FB_PAGE_KEY[_N] -> FB_PAGE_TOKEN[_N], INSTA_PAGE_KEY[_N] -> INSTA_PAGE_TOKEN[_N]."""
    prefix = "FB_PAGE" if platform == "facebook" else "INSTA_PAGE"
    match = re.fullmatch(re.escape(prefix) + r"_KEY(_\d+)?", key_name)
    if not match:
        raise ValueError(f"Invalid {platform} account key '{key_name}'. Expected {prefix}_KEY or {prefix}_KEY_2, etc.")
    return f"{prefix}_TOKEN{match.group(1) or ''}"


def platform_caption(caption: str, platform: str, account: dict) -> str:
    """Add platform-specific CTA; Instagram Reel caption URLs are not clickable."""
    url = str(account.get("profile_url", "")).strip()
    if platform == "facebook":
        cta = "Please like and follow our Facebook Page."
        if url:
            # Facebook recognizes ordinary https URLs in post captions as links.
            cta += f"\nFacebook Page: {url}"
        else:
            print(
                f"WARNING: no profile URL configured for facebook account "
                f"{account.get('account_key', 'unknown')}; add profile_url in config/social_accounts.json."
            )
    else:
        # Instagram does not make URLs in Reel captions clickable. Direct viewers
        # to the profile instead; place any destination URL in the profile's website field.
        cta = "Please like and follow us on Instagram @divineindia247. Visit the link in our bio."
        if url:
            cta += f"\nInstagram profile: {url}"
        else:
            print(
                f"WARNING: no profile URL configured for instagram account "
                f"{account.get('account_key', 'unknown')}; add profile_url in config/social_accounts.json."
            )
    return f"{caption.rstrip()}\n\n{cta}"


def load_accounts(platform_filter: str | None = None, log_skipped: bool = True) -> dict:
    """Resolve configured credentials, optionally for one platform only."""
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
    platforms = (platform_filter,) if platform_filter else ("facebook", "instagram")
    for platform in platforms:
        # A platform can be omitted from the JSON (or set to null/empty) to disable it.
        # This is an intentional skip, not a workflow error.
        mappings = data.get(platform)
        if mappings is None or mappings == {}:
            if log_skipped:
                print(f"INFO: no '{platform}' accounts configured in config/social_accounts.json; skipping platform.")
            continue
        if not isinstance(mappings, dict):
            raise RuntimeError(f"The '{platform}' value in config/social_accounts.json must be an object mapping secret key names to folder arrays, or be omitted to skip the platform.")
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
            if not isinstance(folders, list):
                raise RuntimeError(f"{platform}.{key_env}.folders must be a JSON array.")
            normalized_folders = []
            for folder_entry in folders:
                if isinstance(folder_entry, str) and folder_entry.strip():
                    normalized_folders.append(folder_entry.strip())
                elif isinstance(folder_entry, dict):
                    folder_name = folder_entry.get("name")
                    count = folder_entry.get("count", 1)
                    if not isinstance(folder_name, str) or not folder_name.strip():
                        raise RuntimeError(f"{platform}.{key_env}.folders entries need a non-empty 'name'.")
                    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                        raise RuntimeError(f"{platform}.{key_env}.folders count for {folder_name!r} must be a positive integer.")
                    normalized_folders.append(folder_name.strip())
                else:
                    raise RuntimeError(
                        f"{platform}.{key_env}.folders entries must be strings or objects like "
                        "{\"name\": \"hanumanji\", \"count\": 2}."
                    )
            folders = normalized_folders
            if profile_url and not profile_url.startswith(("https://", "http://")):
                raise RuntimeError(f"{platform}.{key_env}.profile_url must start with https:// or http://.")
            token_env = _paired_token_name(key_env, platform)
            account_id = os.getenv(key_env, "").strip()
            token = os.getenv(token_env, "").strip()
            if not account_id and not token:
                if log_skipped:
                    print(f"INFO: {platform} account '{key_env}' skipped (GitHub secrets not configured).")
                continue
            if not account_id or not token:
                if log_skipped:
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


def post_facebook(video: Path, caption: str, account: dict, folder: str) -> str:
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
    payload = r.json()
    post_id = str(payload.get("id", ""))
    print(f"Facebook published [{folder}] account key {account.get('account_key', '')}, Page {page_id}: {payload}")
    return post_id


def post_instagram(video_url: str, caption: str, account: dict, folder: str) -> str:
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
    payload = publish.json()
    post_id = str(payload.get("id", ""))
    print(f"Instagram published [{folder}] account key {account.get('account_key', '')}, account {user_id}: {payload}")
    return post_id


def _write_result(path: str | None, platform: str, folder: str, video: str, records: list[dict]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "platform": platform,
        "folder": folder,
        "video": video,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "records": records,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish generated Divine India reels.")
    parser.add_argument("target", choices=["facebook", "instagram", "all", "has-instagram"])
    parser.add_argument("--folder", help="Only publish the specified generated folder.")
    parser.add_argument("--video", help="Only publish the specified video filename within --folder.")
    parser.add_argument("--result", help="Write per-account publication statuses to this JSON file.")
    parser.add_argument("--account-key", help="Publish only to this configured GitHub secret key, e.g. FB_PAGE_KEY_2.")
    args = parser.parse_args()
    target = args.target.lower()

    if target == "has-instagram":
        # stdout must contain only a valid GitHub Actions output assignment.
        accounts = load_accounts(platform_filter="instagram", log_skipped=False)
        print("has_instagram=" + str(any(v.get("instagram") for v in accounts.values())).lower())
        return
    if args.video and not args.folder:
        parser.error("--video requires --folder")

    accounts = load_accounts(platform_filter=target if target in {"facebook", "instagram"} else None)
    if args.account_key:
        if target not in {"facebook", "instagram"}:
            parser.error("--account-key can only be used with facebook or instagram")
        for folder_name, platform_map in accounts.items():
            platform_map[target] = [a for a in platform_map.get(target, []) if a.get("account_key") == args.account_key]
    urls = instagram_urls()
    errors: list[str] = []
    records: list[dict] = []
    if not OUT_ROOT.is_dir():
        raise RuntimeError(f"Generated output directory does not exist: {OUT_ROOT}")

    folders = [OUT_ROOT / args.folder] if args.folder else sorted(p for p in OUT_ROOT.iterdir() if p.is_dir())
    for folder_dir in folders:
        if not folder_dir.is_dir():
            errors.append(f"Generated folder not found: {folder_dir.name}")
            continue
        folder = folder_dir.name
        caption_file = folder_dir / "caption.txt"
        if not caption_file.is_file():
            errors.append(f"Missing caption for generated folder: {folder}")
            continue
        videos = sorted(folder_dir.glob("daily_reel*.mp4"), key=lambda path: (path.name != "daily_reel.mp4", path.name))
        if args.video:
            videos = [v for v in videos if v.name == args.video]
        if not videos:
            errors.append(f"No requested generated video found for {folder}/{args.video or '*'}")
            continue

        caption = caption_file.read_text(encoding="utf-8").strip()
        configured = accounts.get(folder, {"facebook": [], "instagram": []})
        platforms = ("facebook", "instagram") if target == "all" else (target,)
        for video in videos:
            video_url = str(urls.get(f"{folder}/{video.name}", urls.get(folder, "") if video.name == "daily_reel.mp4" else ""))
            for platform in platforms:
                destinations = configured.get(platform, [])
                if not destinations:
                    missing_message = (
                        f"Account '{args.account_key}' is not configured with a complete ID/token pair for {platform} and folder '{folder}'."
                        if args.account_key else f"No configured credentials for {platform} and folder '{folder}'."
                    )
                    records.append({
                        "platform": platform, "folder": folder, "video": video.name,
                        "account_key": args.account_key or "", "account_id": "", "status": "FAILED" if args.account_key else "SKIPPED",
                        "post_id": "", "published_at": "", "error": missing_message,
                    })
                    if args.account_key:
                        errors.append(missing_message)
                        print(f"ERROR: {missing_message}")
                    else:
                        print(f"WARNING: {missing_message} Recording SKIPPED.")
                    continue
                for account in destinations:
                    account_key = str(account.get("account_key", "unknown"))
                    account_id = str(account.get("page_id" if platform == "facebook" else "user_id", ""))
                    record = {
                        "platform": platform, "folder": folder, "video": video.name,
                        "account_key": account_key, "account_id": account_id,
                        "status": "FAILED", "post_id": "", "published_at": "", "error": "",
                    }
                    if platform == "facebook":
                        is_blocked, block_reason = _facebook_account_blocked(account_key)
                        if is_blocked:
                            record.update(status="SKIPPED", error=block_reason)
                            print(f"SKIPPED: Facebook account {account_key} for {folder}/{video.name}: {block_reason}")
                            records.append(record)
                            continue
                    try:
                        caption_for_platform = platform_caption(caption, platform, account)
                        if platform == "facebook":
                            post_id = post_facebook(video, caption_for_platform, account, folder)
                        else:
                            post_id = post_instagram(video_url, caption_for_platform, account, folder)
                        record.update(status="PUBLISHED", post_id=post_id,
                                      published_at=datetime.now(timezone.utc).isoformat())
                    except Exception as exc:
                        record["error"] = str(exc)
                        if platform == "facebook" and _is_meta_368(str(exc)):
                            _write_fb_block(account_key, account_id, str(exc))
                            record.update(status="FAILED", error=str(exc))
                            print(f"DAILY ACCOUNT BLOCKED: Facebook {account_key}; subsequent jobs for this account will be skipped today.")
                        errors.append(f"{platform} [{folder}/{video.name}] [{account_key}]: {exc}")
                        print(f"ERROR: {errors[-1]}")
                    records.append(record)

    _write_result(args.result, target, args.folder or "*", args.video or "*", records)
    if records and all(record.get("status") == "PUBLISHED" for record in records):
        print(f"SUCCESS: {target} account {args.account_key or '(all configured accounts)'} published {len(records)} target(s).")
    elif records:
        published = sum(record.get("status") == "PUBLISHED" for record in records)
        failed = sum(record.get("status") == "FAILED" for record in records)
        skipped = sum(record.get("status") == "SKIPPED" for record in records)
        print(f"PUBLICATION SUMMARY: account={args.account_key or '(all)'} published={published}, failed={failed}, skipped={skipped}.")
    if errors:
        raise RuntimeError("One or more publishing targets failed:\n" + "\n".join(errors))


if __name__ == "__main__":
    main()
