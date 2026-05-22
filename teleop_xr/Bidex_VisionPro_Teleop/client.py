"""
Subscribe to Quest headset tracking from Unity VisionProFormatTracking (UDP).

Unity publishes avp_tracking_v1 JSON on port 5006 by default.
This client exposes the same dict keys as avp_stream VisionProStreamer.latest,
so avp_leap.py can use it as a drop-in replacement for Vision Pro.

Usage:
    python client.py
    python client.py --port 5006

In avp_leap.py:
    QUEST_IP = "192.168.x.x"  # Quest Wi-Fi IP
    self.vps = QuestHeadsetStreamer(quest_ip=QUEST_IP, port=5006)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Bidex_VisionPro_Teleop/quest_streamer.py (same folder as this file)
_BIDEX_DIR = Path(__file__).resolve().parent
if str(_BIDEX_DIR) not in sys.path:
    sys.path.insert(0, str(_BIDEX_DIR))

from quest_streamer import (  # noqa: E402
    DEFAULT_QUEST_SUBSCRIBE_PORT,
    QuestVisionProStreamer,
    TrackingData,
)

# Default UDP port (VisionProFormatTracking.cs streamPort)
QUEST_UDP_PORT = 5006


class QuestHeadsetStreamer:
    """
    Receive tracking from Quest Unity app over UDP.

    API mirrors VisionProStreamer fields used by Bidex avp_leap.py:
      - latest: raw dict with head, left/right_wrist, left/right_fingers, etc.
      - get_latest(): TrackingData wrapper (attribute + dict access)
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = QUEST_UDP_PORT,
        quest_ip: Optional[str] = None,
        quest_subscribe_port: int = DEFAULT_QUEST_SUBSCRIBE_PORT,
    ):
        self.host = host
        self.port = port
        self.quest_ip = quest_ip
        self._streamer = QuestVisionProStreamer(
            host=host,
            port=port,
            quest_ip=quest_ip,
            quest_subscribe_port=quest_subscribe_port,
        )

    @property
    def latest(self) -> Optional[Dict[str, Any]]:
        """Raw tracking dict (same keys as VisionProStreamer.latest)."""
        return self._streamer.get_latest_raw()

    def get_latest(self) -> Optional[TrackingData]:
        return self._streamer.get_latest()

    def poll(self) -> Optional[Dict[str, Any]]:
        """Alias for latest (kept for explicit polling in scripts)."""
        return self.latest

    def wait_for_first_packet(self, timeout_sec: float = 30.0) -> Dict[str, Any]:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            sample = self.latest
            if sample is not None:
                return sample
            time.sleep(0.01)
        raise TimeoutError(
            f"No tracking received on UDP {self.host}:{self.port} within {timeout_sec}s.\n"
            "Checklist:\n"
            "  1. Unity is in Play mode (or Quest app is running)\n"
            "  2. VisionProFormatTracking is on the scene and enabled\n"
            "  3. Subscribe mode: set QUEST_IP in avp_leap.py; Unity useSubscribeMode + subscribePort 5007\n"
            "  4. Unity streamPort = 5006 (matches this client)\n"
            "  5. Windows firewall allows UDP 5006 and 5007"
        )

    def close(self) -> None:
        self._streamer.close()


def _print_sample(raw: Dict[str, Any]) -> None:
    head = raw["head"][0, :3, 3]
    lw = raw["left_wrist"][0, :3, 3]
    rw = raw["right_wrist"][0, :3, 3]
    lp = raw["left_pinch_distance"]
    rp = raw["right_pinch_distance"]
    print(
        f"head={head}  "
        f"left_wrist={lw}  right_wrist={rw}  "
        f"pinch L/R={lp:.4f}/{rp:.4f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Subscribe to Quest headset tracking (UDP)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (0.0.0.0 = all interfaces)")
    parser.add_argument("--port", type=int, default=QUEST_UDP_PORT)
    parser.add_argument("--quest-ip", default=None, help="Quest Wi-Fi IP (subscribe mode)")
    parser.add_argument("--quest-subscribe-port", type=int, default=DEFAULT_QUEST_SUBSCRIBE_PORT)
    parser.add_argument("--rate", type=float, default=30.0, help="Print rate (Hz)")
    parser.add_argument("--wait", type=float, default=30.0, help="Seconds to wait for first packet (0 = wait forever)")
    args = parser.parse_args()

    streamer = QuestHeadsetStreamer(
        host=args.host,
        port=args.port,
        quest_ip=args.quest_ip,
        quest_subscribe_port=args.quest_subscribe_port,
    )
    if args.quest_ip:
        print(f"Subscribed to Quest {args.quest_ip}:{args.quest_subscribe_port}, listening on {args.host}:{args.port} ...")
    else:
        print(f"Listening for Quest tracking on {args.host}:{args.port} (pass --quest-ip for subscribe mode) ...")
    print("Start Unity Play mode (or Quest app) now.")
    try:
        if args.wait == 0:
            while streamer.latest is None:
                time.sleep(0.05)
            print("First packet received.")
        else:
            streamer.wait_for_first_packet(timeout_sec=args.wait)
            print("First packet received.")
        interval = 1.0 / args.rate
        while True:
            raw = streamer.latest
            if raw is not None:
                _print_sample(raw)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        streamer.close()


if __name__ == "__main__":
    main()
