"""IndexNow client — push URL changes to Bing + Yandex without polling.

IndexNow (https://www.indexnow.org/) is the open protocol Bing/Yandex
expose for on-demand URL submission. Google doesn't honour it, but
Bing's index drives Bing+DuckDuckGo+Yahoo+Brave search results.

Flow:
  1. We host a key file at https://predictor.nullshift.sh/{KEY}.txt
     containing just the key — Bing reads this to verify ownership.
  2. POST a JSON body to https://api.indexnow.org/IndexNow with the
     URLs we want re-crawled.
  3. Bing crawls within minutes (vs days for sitemap polling).

Keys live in INDEXNOW_KEY env var. Skips silently when unset.
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Iterable


SITE = "https://predictor.nullshift.sh"
ENDPOINT = "https://api.indexnow.org/IndexNow"


def submit(urls: Iterable[str]) -> bool:
    """POST a batch of URLs to IndexNow. Returns True on 200/202."""
    key = os.environ.get("INDEXNOW_KEY")
    if not key:
        return False
    url_list = [u for u in urls if u.startswith(SITE)]
    if not url_list:
        return False
    body = json.dumps({
        "host": "predictor.nullshift.sh",
        "key": key,
        "keyLocation": f"{SITE}/{key}.txt",
        "urlList": url_list,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 202)
    except Exception as e:
        print(f"[indexnow] submit failed: {type(e).__name__}: {e}")
        return False
