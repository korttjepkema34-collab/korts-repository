#!/usr/bin/env python3
"""Send a Wake-on-LAN packet to the gaming PC. Cross-platform (Windows server friendly).
Reads GPU_MAC and LAN_BROADCAST from server/.env or the environment."""
import os, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
env = root / "server" / ".env"
if env.exists():
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
sys.path.insert(0, str(root / "server"))
from orchestrator.wake import send_magic_packet
send_magic_packet(os.environ["GPU_MAC"], os.environ.get("LAN_BROADCAST", "255.255.255.255"))
print("sent wake packet to", os.environ["GPU_MAC"])
