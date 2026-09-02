"""Wake-on-LAN for the gaming PC. Only fires when jobs are queued and the worker is silent."""
from __future__ import annotations

import os
import socket
import time

_last_wake = 0.0


def send_magic_packet(mac: str, broadcast: str) -> None:
    mac_bytes = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    packet = b"\xff" * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(packet, (broadcast, 9))


def maybe_wake(queued_jobs: int, worker_alive: bool, cooldown_s: int = 900) -> bool:
    """Send a wake at most once per cooldown when work is waiting and the worker is offline."""
    global _last_wake
    if queued_jobs == 0 or worker_alive:
        return False
    if time.time() - _last_wake < cooldown_s:
        return False
    mac = os.environ.get("GPU_MAC")
    bcast = os.environ.get("LAN_BROADCAST", "255.255.255.255")
    if not mac or mac.startswith("AA:BB"):
        return False
    send_magic_packet(mac, bcast)
    _last_wake = time.time()
    return True
