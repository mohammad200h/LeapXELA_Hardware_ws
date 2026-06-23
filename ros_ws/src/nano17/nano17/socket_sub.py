"""
socket_sub.py
=============

WebSocket subscriber for force_sensor_data_collection_only.py.

Connects to the force sensor stream and prints each sample as it arrives.
"""

import argparse
import asyncio
import json
from datetime import datetime

from websockets import connect


def print_sample(timestamp_s: float, fx: float, fy: float, fz: float):
    ts = datetime.now().strftime("%H:%M:%S")
    print(
        f"[{ts}] t={timestamp_s:.6f}  "
        f"Fx={fx:.6f}  Fy={fy:.6f}  Fz={fz:.6f}",
        flush=True,
    )


async def subscribe(uri: str):
    print(f"Connecting to {uri} ...", flush=True)

    async with connect(uri) as websocket:
        print(f"Connected to {uri}", flush=True)

        async for message in websocket:
            data = json.loads(message)

            timestamps = data["timestamp_s"]
            fx_values = data["Fx"]
            fy_values = data["Fy"]
            fz_values = data["Fz"]

            for timestamp_s, fx, fy, fz in zip(
                timestamps, fx_values, fy_values, fz_values
            ):
                print_sample(timestamp_s, fx, fy, fz)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Subscribe to NI-DAQ force sensor WebSocket stream."
    )
    parser.add_argument(
        "--host",
        type=str,
        default="192.168.2.59",
        help="WebSocket server host. Default: localhost",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port. Default: 8765",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    uri = f"ws://{args.host}:{args.port}"

    try:
        asyncio.run(subscribe(uri))
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)


if __name__ == "__main__":
    main()
