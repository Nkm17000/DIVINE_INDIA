import os, time, requests
from pathlib import Path
from .config import *

def _graph(path, token, method="POST", **kwargs):
    url=f"https://graph.facebook.com/{META_GRAPH_VERSION}/{path.lstrip('/')}"
    r=requests.request(method, url, params={"access_token":token}, timeout=60, **kwargs)
    try: data=r.json()
    except Exception: data={"raw":r.text}
    if not r.ok or "error" in data:
        raise RuntimeError(f"Meta API error {r.status_code}: {data}")
    return data

def post_facebook(video_path, caption):
    # Page video upload. This publishes the generated reel-style MP4 as a Page video.
    with open(video_path,"rb") as f:
        data=_graph(f"{FB_PAGE_ID}/videos", FB_PAGE_ACCESS_TOKEN,
                    files={"source":("daily_reel.mp4",f,"video/mp4")},
                    data={"description":caption,"published":"true"})
    return data

def _wait_ig(container_id):
    for _ in range(30):
        d=_graph(container_id, IG_ACCESS_TOKEN, method="GET")
        status=d.get("status_code")
        if status in ("FINISHED","PUBLISHED"):
            return d
        if status in ("ERROR","EXPIRED"):
            raise RuntimeError(f"Instagram container failed: {d}")
        time.sleep(5)
    raise TimeoutError("Instagram media container did not finish in time")

def post_instagram(video_url, caption):
    if not video_url.startswith("http"):
        raise ValueError("Instagram requires PUBLIC_VIDEO_URL or a public GitHub release asset URL.")
    data=_graph(f"{IG_USER_ID}/media", IG_ACCESS_TOKEN,
                data={"media_type":"REELS","video_url":video_url,"caption":caption})
    container=data["id"]
    _wait_ig(container)
    return _graph(f"{IG_USER_ID}/media_publish", IG_ACCESS_TOKEN,
                  data={"creation_id":container})
