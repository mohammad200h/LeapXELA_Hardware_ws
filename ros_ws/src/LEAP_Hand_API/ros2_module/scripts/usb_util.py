"""Locate the LEAP hand's U2D2 (FTDI FT232H) serial port.

Python port of shell/find_leapXela_USB.sh: match USB serial devices on vendor/product id
instead of assuming a fixed /dev/ttyUSB* number.
"""

from serial.tools import list_ports

TARGET_VENDOR_ID = 0x0403
TARGET_MODEL_ID = 0x6014


def find_leap_hand_ports():
    """Return the device paths (e.g. '/dev/ttyUSB0') of all matching FT232H adapters."""
    return sorted(
        p.device for p in list_ports.comports()
        if p.vid == TARGET_VENDOR_ID and p.pid == TARGET_MODEL_ID
    )


def find_leap_hand_port():
    """Return the single matching device path; raise if none or more than one is found."""
    ports = find_leap_hand_ports()
    if len(ports) != 1:
        details = "\n".join(
            f"  - {p.device} (serial={p.serial_number} desc={p.description})"
            for p in list_ports.comports()
            if p.vid == TARGET_VENDOR_ID and p.pid == TARGET_MODEL_ID
        ) or "  (none)"
        raise RuntimeError(
            f"Expected 1 LEAP hand device ({TARGET_VENDOR_ID:04x}:{TARGET_MODEL_ID:04x}) "
            f"but found {len(ports)}:\n{details}\n"
            f"Tip: run 'lsusb | grep {TARGET_VENDOR_ID:04x}:{TARGET_MODEL_ID:04x}'."
        )
    return ports[0]


if __name__ == "__main__":
    print(find_leap_hand_port())
