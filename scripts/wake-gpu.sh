#!/usr/bin/env bash
# Send a Wake-on-LAN packet to the gaming PC. Reads GPU_MAC and LAN_BROADCAST from server/.env.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source server/.env; set +a
if command -v wakeonlan >/dev/null; then
  wakeonlan -i "${LAN_BROADCAST:-255.255.255.255}" "$GPU_MAC"
else
  python3 - "$GPU_MAC" "${LAN_BROADCAST:-255.255.255.255}" << 'PY'
import socket, sys
mac, bcast = sys.argv[1], sys.argv[2]
pkt = b"\xff"*6 + bytes.fromhex(mac.replace(":", "").replace("-", ""))*16
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.sendto(pkt, (bcast, 9)); print("sent")
PY
fi
