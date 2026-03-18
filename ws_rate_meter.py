#!/usr/bin/env python3
import argparse
import threading
import time
from typing import Dict, Optional

from websocket import WebSocketApp


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure WebSocket message rate (msg/s) per port.")
    ap.add_argument("--host", default="127.0.0.1", help="WebSocket host/IP (default: 127.0.0.1)")
    ap.add_argument("--ports", default="5000,5001", help="Comma-separated ports (default: 5000,5001)")
    ap.add_argument("--interval", type=float, default=1.0, help="Print interval seconds (default: 1.0)")
    ap.add_argument("--duration", type=float, default=0.0, help="Stop after N seconds (0 = run forever)")
    args = ap.parse_args()

    ports = [int(p.strip()) for p in args.ports.split(",") if p.strip()]
    if not ports:
        raise SystemExit("No ports provided.")

    counts: Dict[int, int] = {p: 0 for p in ports}
    errs: Dict[int, Optional[str]] = {p: None for p in ports}
    lock = threading.Lock()
    t0 = time.time()

    def make_handlers(p: int):
        def on_message(_ws, _msg: str):
            with lock:
                counts[p] += 1

        def on_error(_ws, err: Exception):
            with lock:
                errs[p] = repr(err)

        def on_close(_ws, *_args):
            with lock:
                if errs[p] is None:
                    errs[p] = "closed"

        return on_message, on_error, on_close

    for p in ports:
        url = f"ws://{args.host}:{p}"
        on_message, on_error, on_close = make_handlers(p)
        ws = WebSocketApp(url, on_message=on_message, on_error=on_error, on_close=on_close)
        threading.Thread(target=ws.run_forever, daemon=True).start()

    while True:
        time.sleep(args.interval)
        now = time.time()
        dt = now - t0
        with lock:
            line = " ".join([f"{p}: {counts[p]/dt:.1f} msg/s" for p in ports])
            errline = " ".join([f"{p}: {errs[p]}" for p in ports if errs[p] is not None])
        print(line, flush=True)
        if errline:
            print(f"errors: {errline}", flush=True)
        if args.duration and dt >= args.duration:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())

