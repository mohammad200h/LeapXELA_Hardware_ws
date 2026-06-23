"""
force_publisher_6d.py
=====================

Standalone six-axis force/torque sensor acquisition and WebSocket publisher.

The NI-DAQ and calibration settings match arm_DataCollection.py. Published
WebSocket messages use this JSON format:

    {
        "timestamp_s": [t0, t1, ...],
        "Fx": [...],
        "Fy": [...],
        "Fz": [...],
        "Tx": [...],
        "Ty": [...],
        "Tz": [...]
    }
"""

from __future__ import annotations

import argparse
import asyncio
import json
import queue
import threading
import time
from datetime import datetime

import nidaqmx
import numpy as np
from nidaqmx.constants import AcquisitionType, TerminalConfiguration
from scipy.signal import butter, sosfiltfilt
from websockets import serve


# ==============================================================================
# LOGGING
# ==============================================================================

def _log(level: str, message: str):
    print(f"[{datetime.now():%H:%M:%S}] {level}: {message}", flush=True)


def print_info(message: str):
    _log("INFO", message)


def print_warning(message: str):
    _log("WARN", message)


def print_error(message: str):
    _log("ERROR", message)


# ==============================================================================
# SIX-AXIS FORCE/TORQUE SENSOR CONFIGURATION
# ==============================================================================

# These values are copied from arm_DataCollection.py.
DAQ_DEVICE = "Dev1"
DAQ_CHANNELS = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5"]
SAMPLE_RATE = 1600
SAMPLES_PER_READ = 160
BUFFER_SIZE = 3200
VOLTAGE_SCALING = 0.032
FILTER_CUTOFF_HZ = 40

# Output order: Fx, Fy, Fz, Tx, Ty, Tz.
CALIBRATION_MATRIX = np.array([
    [
        2.792168191,
        0.115797332,
        -2.485212270,
        -37.546617700,
        0.030840735,
        36.550459290,
    ],
    [
        -0.389492650,
        42.577690120,
        2.535232767,
        -21.453301400,
        -3.788663480,
        -21.395116700,
    ],
    [
        60.232215840,
        -1.413852120,
        59.832975870,
        0.596193548,
        60.164001280,
        0.653726313,
    ],
    [
        -0.028203730,
        0.910380207,
        -2.071419030,
        -0.478986150,
        2.099582569,
        -0.433084920,
    ],
    [
        2.410217915,
        -0.056155140,
        -1.158583940,
        0.801226223,
        -1.261772320,
        -0.808731680,
    ],
    [
        -0.001844810,
        -1.328327540,
        -0.047889410,
        -1.345714670,
        -0.026464630,
        -1.321034410,
    ],
])


# ==============================================================================
# WEBSOCKET PUBLISHER
# ==============================================================================

class ForceWebSocketPublisher:
    """Thread-safe WebSocket broadcaster for force/torque samples."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self._clients: set = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def start(self):
        self._thread = threading.Thread(
            target=self._run_server,
            name="force-torque-websocket-server",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            raise RuntimeError("WebSocket server did not start in time.")

    def stop(self):
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def publish(self, payload: dict):
        if not self._clients or self._loop is None:
            return

        message = json.dumps(payload)
        asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)

    def _run_server(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        async with serve(self._handler, self.host, self.port):
            print_info(f"WebSocket server listening on ws://{self.host}:{self.port}")
            self._ready.set()
            await asyncio.Future()

    async def _handler(self, websocket):
        self._clients.add(websocket)
        print_info(f"WebSocket client connected ({len(self._clients)} total)")
        try:
            await websocket.wait_closed()
        finally:
            self._clients.discard(websocket)
            print_info(f"WebSocket client disconnected ({len(self._clients)} total)")

    async def _broadcast(self, message: str):
        dead_clients = []
        for client in self._clients.copy():
            try:
                await client.send(message)
            except Exception:
                dead_clients.append(client)

        for client in dead_clients:
            self._clients.discard(client)


# ==============================================================================
# SIX-AXIS FORCE/TORQUE SENSOR
# ==============================================================================

class ForceTorqueSensor:
    """Continuous six-channel NI-DAQ force/torque acquisition."""

    def __init__(self):
        self._sos = butter(
            4,
            FILTER_CUTOFF_HZ / (SAMPLE_RATE / 2),
            btype="low",
            output="sos",
        )
        self._ref_voltage = None
        self._raw_queue: queue.SimpleQueue = queue.SimpleQueue()
        self._task = None
        self._running = False
        self._process_thread: threading.Thread | None = None
        self._publisher: ForceWebSocketPublisher | None = None

        self.latest_forces = np.zeros(6)
        self._sample_count = 0
        self._report_t0 = time.time()

    def attach_publisher(self, publisher: ForceWebSocketPublisher):
        self._publisher = publisher

    def detach_publisher(self):
        self._publisher = None

    def start(self):
        self._task = nidaqmx.Task()

        for channel in DAQ_CHANNELS:
            self._task.ai_channels.add_ai_voltage_chan(
                f"{DAQ_DEVICE}/{channel}",
                terminal_config=TerminalConfiguration.RSE,
            )

        self._task.timing.cfg_samp_clk_timing(
            rate=SAMPLE_RATE,
            sample_mode=AcquisitionType.CONTINUOUS,
            samps_per_chan=BUFFER_SIZE,
        )
        self._task.in_stream.input_buf_size = BUFFER_SIZE
        self._task.register_every_n_samples_acquired_into_buffer_event(
            SAMPLES_PER_READ,
            self._daq_callback,
        )

        self._running = True
        self._process_thread = threading.Thread(
            target=self._process_loop,
            name="force-torque-processing",
            daemon=True,
        )
        self._process_thread.start()
        self._task.start()
        print_info("Six-axis force/torque sensor started.")

    def stop(self):
        self._running = False

        if self._task is not None:
            try:
                self._task.stop()
                self._task.close()
            except Exception as exc:
                print_warning(f"Error while stopping DAQ task: {exc}")
            finally:
                self._task = None

        if self._process_thread is not None:
            self._process_thread.join(timeout=1.0)
            self._process_thread = None

        print_info("Six-axis force/torque sensor stopped.")

    def _daq_callback(self, task_handle, event_type, n_samples, callback_data):
        try:
            raw = np.asarray(
                self._task.read(number_of_samples_per_channel=n_samples),
                dtype=float,
            )
            if raw.ndim == 1:
                raw = raw.reshape(1, -1)

            # NI-DAQ returns (channels, samples); processing uses (samples, channels).
            self._raw_queue.put((time.time(), raw.T))
        except Exception as exc:
            print_error(f"Force DAQ callback error: {exc}")

        return 0

    def _process_loop(self):
        while self._running:
            try:
                t_end, raw = self._raw_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._process_batch(t_end, raw)
            except Exception as exc:
                print_error(f"Force processing error: {exc}")

    def _process_batch(self, t_end: float, raw: np.ndarray):
        n = raw.shape[0]

        if self._ref_voltage is None:
            self._ref_voltage = np.mean(raw, axis=0)
            print_info(
                "Force reference voltage set: "
                + ", ".join(f"{value:.6f}" for value in self._ref_voltage)
            )

        filtered = sosfiltfilt(self._sos, raw, axis=0)
        voltage = (filtered - self._ref_voltage) * VOLTAGE_SCALING
        forces = (CALIBRATION_MATRIX @ voltage.T).T

        t_start = t_end - n / SAMPLE_RATE
        timestamps = np.linspace(t_start, t_end, n, endpoint=False)

        self.latest_forces = forces[-1].copy()
        self._sample_count += n

        if self._publisher is not None:
            self._publisher.publish({
                "timestamp_s": timestamps.tolist(),
                "Fx": forces[:, 0].tolist(),
                "Fy": forces[:, 1].tolist(),
                "Fz": forces[:, 2].tolist(),
                "Tx": forces[:, 3].tolist(),
                "Ty": forces[:, 4].tolist(),
                "Tz": forces[:, 5].tolist(),
            })

        now = time.time()
        if now - self._report_t0 >= 1.0:
            frequency = self._sample_count / (now - self._report_t0)
            fx, fy, fz, tx, ty, tz = self.latest_forces
            print_info(
                f"Force sampling: {frequency:.1f} Hz | "
                f"F=[{fx:.3f}, {fy:.3f}, {fz:.3f}] N | "
                f"T=[{tx:.3f}, {ty:.3f}, {tz:.3f}] Nm"
            )
            self._sample_count = 0
            self._report_t0 = now

    @property
    def force_magnitude(self) -> float:
        return float(np.linalg.norm(self.latest_forces[:3]))


# ==============================================================================
# MAIN
# ==============================================================================

def collect_force_data(
    duration: float | None = None,
    host: str = "0.0.0.0",
    port: int = 8765,
):
    """Publish six-axis force/torque data until Ctrl+C or duration expires."""

    publisher = ForceWebSocketPublisher(host=host, port=port)
    force_sensor = ForceTorqueSensor()

    try:
        publisher.start()
        force_sensor.attach_publisher(publisher)
        force_sensor.start()

        print_info("Waiting for force reference...")
        t0 = time.time()
        while force_sensor._ref_voltage is None:
            if time.time() - t0 > 10:
                raise RuntimeError("Force sensor did not initialise.")
            time.sleep(0.05)

        print_info("Streaming six-axis data over WebSocket. Press Ctrl+C to stop.")
        start_time = time.time()

        while True:
            if duration is not None and time.time() - start_time >= duration:
                print_info("Requested duration reached.")
                break
            time.sleep(0.1)

    except KeyboardInterrupt:
        print_warning("Interrupted by user.")
    finally:
        force_sensor.detach_publisher()
        force_sensor.stop()
        publisher.stop()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Six-axis NI-DAQ force/torque WebSocket publisher."
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional streaming duration in seconds. Default: until Ctrl+C.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="WebSocket bind address. Default: 0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket port. Default: 8765",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    collect_force_data(duration=args.duration, host=args.host, port=args.port)
