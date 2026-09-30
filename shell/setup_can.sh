#!/usr/bin/env bash
#
# setup_can.sh - bring up the two LeapXela USB-CAN adapters as can0 / can1.
#
# The adapters are discovered by their FTDI serial via /dev/serial/by-id, never
# by /dev/ttyUSBn: those numbers come from kernel enumeration order, so a reboot,
# a replug, or the LEAP hand's own FT232H claiming a slot silently swaps them.
#
# After bring-up the script *verifies* the assignment by counting the unique CAN
# IDs actually arriving on each bus, and re-attaches the adapters the other way
# round if they are reversed. That makes bring-up correct regardless of both USB
# enumeration order and which CAN connector is plugged into which adapter.
#
# Usage:
#   ./setup_can.sh                             # discover, attach, verify, self-correct
#   ./setup_can.sh /dev/ttyUSB2 /dev/ttyUSB1   # manual override (skips discovery)
#   SKIP_PROBE=1 ./setup_can.sh                # attach only, no verification

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# Expected unique 11-bit CAN IDs per bus. Derived from etc_xela/xServ_leap.ini
# (channel = can0,can1 ; model = leap) and the 368-taxel LEAP.xela definition:
#   can0 -> 296 IDs : 4 fingertips (30 taxels each) + 11 4x4 pads (16 each) = 296 taxels
#   can1 ->  72 IDs : 3 palm 4x6 pads (24 taxels each)                      =  72 taxels
EXPECTED_CAN0_IDS=${EXPECTED_CAN0_IDS:-296}
EXPECTED_CAN1_IDS=${EXPECTED_CAN1_IDS:-72}

SLCAND_OPTS=(-o -s8 -t hw -S 3000000) # -s8 = 1 Mbit/s CAN, -S = 3 Mbaud serial
PROBE_SECS=${PROBE_SECS:-1}
SKIP_PROBE=${SKIP_PROBE:-0}

# ------------------------------------------------------------- discovery -----
if [ "$#" -eq 1 ]; then
  echo "Give either zero devices (auto-discover) or two." >&2
  exit 1
elif [ "$#" -ge 2 ]; then
  DEV0="$1"
  DEV1="$2"
  LABEL0="$DEV0"
  LABEL1="$DEV1"
  echo "Using devices given on the command line: $DEV0 -> can0, $DEV1 -> can1"
else
  # find_Xela_sensor_device_name.sh already walks /dev/serial/by-id, filters on
  # VID:PID 0403:6015, de-dupes, and enforces exactly two matches. Reuse it and
  # take the stable by-id path out of its output rather than the ttyUSB node.
  echo "Discovering USB-CAN adapters by FTDI serial ..."
  if ! found=$(./find_Xela_sensor_device_name.sh); then
    echo "$found" >&2
    echo "Could not identify exactly two USB-CAN adapters. Aborting." >&2
    exit 1
  fi

  # Sorted by by-id name so the first attempt is deterministic across runs
  # (find(1) returns directory order); the probe below corrects it either way.
  byids=()
  serials=()
  while IFS='|' read -r byid serial; do
    [ -n "$byid" ] || continue
    byids+=("/dev/serial/by-id/$byid")
    serials+=("${serial:-?}")
  done < <(
    while IFS= read -r line; do
      case "$line" in /dev/*) ;; *) continue ;; esac
      sed -n 's/.*by-id=\([^ )]*\).*serial=\([^ )]*\).*/\1|\2/p' <<<"$line"
    done <<<"$found" | sort
  )

  if [ "${#byids[@]}" -ne 2 ]; then
    echo "Expected 2 by-id paths, parsed ${#byids[@]} from:" >&2
    echo "$found" >&2
    exit 1
  fi

  DEV0="${byids[0]}"
  DEV1="${byids[1]}"
  LABEL0="serial ${serials[0]}"
  LABEL1="serial ${serials[1]}"
fi

# --------------------------------------------------------------- attach ------
teardown() {
  echo "Tearing down existing CAN interfaces ..."
  ./reset_can.sh >/dev/null 2>&1 || true
  sleep 0.5
}

attach() {
  # Resolve by-id symlinks to the concrete node: slcand takes a plain tty name,
  # and resolving here (not at discovery) picks up any replug in between.
  local dev0 dev1 i
  dev0=$(readlink -f "$1")
  dev1=$(readlink -f "$2")
  [ -c "$dev0" ] && [ -c "$dev1" ] || {
    echo "Not character devices: $dev0 / $dev1" >&2
    exit 1
  }

  sudo modprobe slcan
  sudo slcand "${SLCAND_OPTS[@]}" "$dev0" can0
  sudo slcand "${SLCAND_OPTS[@]}" "$dev1" can1

  # slcand creates the netdev asynchronously; wait for both to appear.
  for i in $(seq 1 50); do
    [ -d /sys/class/net/can0 ] && [ -d /sys/class/net/can1 ] && break
    sleep 0.1
  done
  if [ ! -d /sys/class/net/can0 ] || [ ! -d /sys/class/net/can1 ]; then
    echo "slcand did not create can0/can1. Check that $dev0 and $dev1 are the adapters." >&2
    exit 1
  fi

  sudo ip link set up can0
  sudo ip link set up can1
}

if [ -d /sys/class/net/can0 ] || [ -d /sys/class/net/can1 ]; then
  teardown
fi

echo "Attaching $DEV0 ($LABEL0) -> can0"
echo "Attaching $DEV1 ($LABEL1) -> can1"
attach "$DEV0" "$DEV1"

# ---------------------------------------------------------------- probe ------
if [ "$SKIP_PROBE" = "1" ]; then
  echo "SKIP_PROBE=1 - bringing up without verification."
  echo "can0 <- $LABEL0 ; can1 <- $LABEL1"
  exit 0
fi

if ! command -v candump >/dev/null 2>&1; then
  echo "WARNING: candump not found (sudo apt install can-utils) - cannot verify the"
  echo "         can0/can1 assignment. Interfaces are up but may be reversed."
  exit 0
fi

# Sensors stream continuously with no request, so a passive listen is enough to
# tell the two harnesses apart: 296 unique IDs (fingers + thumb) vs 72 (palm).
# The trailing `|| true` matters: timeout exits 124, and grep exits 1 on a fully
# silent bus. Under `set -o pipefail` either would abort the script instead of
# letting us report a count of 0, which is the case most worth reporting.
count_ids() {
  timeout "$PROBE_SECS" candump -L "$1" 2>/dev/null |
    awk -F'[ #]' '{print $3}' | tr 'a-f' 'A-F' | grep -E '^[0-9A-F]+$' | sort -u | wc -l || true
}

probe() {
  echo "Verifying bus assignment (${PROBE_SECS}s listen) ..."
  N0=$(count_ids can0)
  N1=$(count_ids can1)
  echo "  can0: $N0 unique CAN IDs (expect $EXPECTED_CAN0_IDS)"
  echo "  can1: $N1 unique CAN IDs (expect $EXPECTED_CAN1_IDS)"
}

probe

if [ "$N0" -eq "$EXPECTED_CAN0_IDS" ] && [ "$N1" -eq "$EXPECTED_CAN1_IDS" ]; then
  echo
  echo "OK - can0 <- $LABEL0 ; can1 <- $LABEL1"
  exit 0
fi

if [ "$N0" -eq "$EXPECTED_CAN1_IDS" ] && [ "$N1" -eq "$EXPECTED_CAN0_IDS" ]; then
  echo
  echo "Adapters are reversed - re-attaching the other way round ..."
  teardown
  echo "Attaching $DEV1 ($LABEL1) -> can0"
  echo "Attaching $DEV0 ($LABEL0) -> can1"
  attach "$DEV1" "$DEV0"
  probe
  if [ "$N0" -eq "$EXPECTED_CAN0_IDS" ] && [ "$N1" -eq "$EXPECTED_CAN1_IDS" ]; then
    echo
    echo "OK - can0 <- $LABEL1 ; can1 <- $LABEL0"
    exit 0
  fi
  echo "Still wrong after swapping. Run ./check_xela_can.sh for detail." >&2
  exit 1
fi

echo
echo "Unexpected ID counts - not guessing. Interfaces are up but the taxel map"
echo "will not line up. A count of 0 means that adapter or the hand is unpowered;"
echo "a low count means part of a daisy-chain is silent."
echo "Run ./check_xela_can.sh for a per-ID breakdown." >&2
exit 1
