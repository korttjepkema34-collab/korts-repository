"""Optional push notifications through ntfy (free): set NOTIFY_URL=https://ntfy.sh/<your-topic>
in server/.env and subscribe to the topic in the ntfy app. Off when unset. Never blocks."""
from __future__ import annotations

import os
import urllib.request


def send(title: str, body: str, priority: str = "default") -> None:
    url = os.environ.get("NOTIFY_URL", "").strip()
    if not url:
        return
    try:
        req = urllib.request.Request(url, data=body.encode("utf-8")[:4000], headers={"Title": title[:120], "Priority": priority})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass
