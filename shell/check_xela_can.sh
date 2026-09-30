#!/usr/bin/env bash
#
# check_xela_can.sh - read-only diagnostic for the LeapXela SocketCAN bring-up.
#
# Answers one question: when taxels show up dead in xela_viz, is that a wiring
# problem (the two USB-CAN adapters attached to the wrong interface names) or a
# real hardware fault (a module or daisy-chain that has stopped transmitting)?
#
# Strictly passive: it only listens with candump and reads /sys counters, so it
# is safe to run while xela_server and xela_viz are live.
#
# Usage:
#   ./check_xela_can.sh [can0-iface] [can1-iface]
#   PROBE_SECS=3 ./check_xela_can.sh          # longer capture for a slow bus
#
# Exit codes: 0 = OK, 1 = reversed, 2 = missing IDs / hardware, 3 = setup error.

set -euo pipefail

CAN0=${1:-can0}
CAN1=${2:-can1}
PROBE_SECS=${PROBE_SECS:-1}
SERVER_LOG=${SERVER_LOG:-/etc/xela/LOG/xela_server.log}

# Expected unique 11-bit CAN IDs per bus. Derived from etc_xela/xServ_leap.ini
# (channel = can0,can1 ; model = leap) and the 368-taxel LEAP.xela definition:
#   can0 -> 296 IDs : 4 fingertips (30 taxels each) + 11 4x4 pads (16 each) = 296 taxels
#   can1 ->  72 IDs : 3 palm 4x6 pads (24 taxels each)                      =  72 taxels
EXPECTED_CAN0_IDS=${EXPECTED_CAN0_IDS:-296}
EXPECTED_CAN1_IDS=${EXPECTED_CAN1_IDS:-72}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

command -v candump >/dev/null 2>&1 || {
  echo "candump not found. Install can-utils:  sudo apt install can-utils" >&2
  exit 3
}

for iface in "$CAN0" "$CAN1"; do
  if [ ! -d "/sys/class/net/$iface" ]; then
    echo "Interface '$iface' does not exist. Run ./setup_can.sh first." >&2
    exit 3
  fi
done

# ---------------------------------------------------------------- capture ----
# candump -L emits:  (1785942035.848689) can0 123#DEADBEEF
# so field 3 (splitting on space or '#') is the raw hex ID.
capture() {
  local iface=$1 out=$2
  timeout "$PROBE_SECS" candump -L "$iface" >"$out" 2>/dev/null || true
}

echo "Probing $CAN0 and $CAN1 for ${PROBE_SECS}s ..."
capture "$CAN0" "$WORK/raw0" &
p0=$!
capture "$CAN1" "$WORK/raw1" &
p1=$!
wait "$p0" || true
wait "$p1" || true

# `|| true`: grep exits 1 on a fully silent bus, which under `set -o pipefail`
# would abort instead of reporting the empty set we actually want to see.
ids_from() {
  awk -F'[ #]' '{print $3}' "$1" | tr 'a-f' 'A-F' | grep -E '^[0-9A-F]+$' | sort -u || true
}

ids_from "$WORK/raw0" >"$WORK/seen0"
ids_from "$WORK/raw1" >"$WORK/seen1"

frames0=$(wc -l <"$WORK/raw0")
frames1=$(wc -l <"$WORK/raw1")
n0=$(wc -l <"$WORK/seen0")
n1=$(wc -l <"$WORK/seen1")

# ------------------------------------------------------------ link health ----
stat_of() { cat "/sys/class/net/$1/statistics/$2" 2>/dev/null || echo "?"; }

link_health() {
  local iface=$1
  local line
  # "re-started bus-errors arbit-lost error-warn error-pass bus-off" values sit
  # on the line after that header in `ip -details link show`.
  line=$(ip -details -statistics link show "$iface" 2>/dev/null |
    grep -A1 'bus-errors' | tail -1 | awk '{print $1, $2, $3, $4, $5, $6}')
  echo "    can state : $(ip -details link show "$iface" 2>/dev/null | grep -oE 'can state [A-Z-]+' | head -1 | cut -d' ' -f3-)"
  echo "    restarts/bus-errors/arb-lost/err-warn/err-pass/bus-off : $line"
  echo "    rx_errors=$(stat_of "$iface" rx_errors) rx_dropped=$(stat_of "$iface" rx_dropped)" \
    "rx_over_errors=$(stat_of "$iface" rx_over_errors) rx_frame_errors=$(stat_of "$iface" rx_frame_errors)"
}

echo
echo "=============================== BUS TRAFFIC ==============================="
printf '  %-6s  frames=%-7s unique IDs=%-5s (expected %s)\n' \
  "$CAN0" "$frames0" "$n0" "$EXPECTED_CAN0_IDS"
link_health "$CAN0"
printf '  %-6s  frames=%-7s unique IDs=%-5s (expected %s)\n' \
  "$CAN1" "$frames1" "$n1" "$EXPECTED_CAN1_IDS"
link_health "$CAN1"

# ------------------------------------------------- expected ID sets, if any ---
# xela_server logs its full ID map at startup:
#   ['Server 0 is adding 320 to the system (800)']
# Server 0 reads the first channel, server 1 the second; server 1's decimals
# carry a 0x1000 (4096) bus flag that is not on the wire.
have_expected=0
if [ -r "$SERVER_LOG" ] && grep -q "Started server on port" "$SERVER_LOG" 2>/dev/null; then
  start=$(grep -n "Started server on port" "$SERVER_LOG" | tail -1 | cut -d: -f1)
  tail -n +"$start" "$SERVER_LOG" |
    grep -oE "Server [0-9]+ is adding [0-9a-fA-F]+ to the system \([0-9]+\)" |
    sed -E 's/Server ([0-9]+) is adding [0-9a-fA-F]+ to the system \(([0-9]+)\)/\1 \2/' \
      >"$WORK/reg" || true
  if [ -s "$WORK/reg" ]; then
    awk '$1==0{printf "%03X\n",$2}'      "$WORK/reg" | sort -u >"$WORK/exp0"
    awk '$1==1{printf "%03X\n",$2-4096}' "$WORK/reg" | sort -u >"$WORK/exp1"
    [ -s "$WORK/exp0" ] && [ -s "$WORK/exp1" ] && have_expected=1
  fi
fi

count() { wc -l <"$1"; }

if [ "$have_expected" -eq 1 ]; then
  e0=$(count "$WORK/exp0")
  e1=$(count "$WORK/exp1")
  # as-wired
  miss0=$(comm -13 "$WORK/seen0" "$WORK/exp0" | wc -l)
  miss1=$(comm -13 "$WORK/seen1" "$WORK/exp1" | wc -l)
  # swapped
  smiss0=$(comm -13 "$WORK/seen1" "$WORK/exp0" | wc -l)
  smiss1=$(comm -13 "$WORK/seen0" "$WORK/exp1" | wc -l)

  echo
  echo "======================= ID MAP (from xela_server log) ======================"
  echo "  server 0 -> $CAN0 expects $e0 IDs, server 1 -> $CAN1 expects $e1 IDs"
  printf '  as-wired : %s matched %s/%s   %s matched %s/%s\n' \
    "$CAN0" "$((e0 - miss0))" "$e0" "$CAN1" "$((e1 - miss1))" "$e1"
  printf '  swapped  : %s matched %s/%s   %s matched %s/%s\n' \
    "$CAN0" "$((e0 - smiss0))" "$e0" "$CAN1" "$((e1 - smiss1))" "$e1"
fi

# ------------------------------------------------------------- diagnosis -----
group_report() {
  # Group a list of hex IDs by leading nibble; a whole silent group means one
  # daisy-chain is down, scattered gaps mean individual modules.
  awk '{print substr($0,1,1)}' "$1" | sort | uniq -c |
    awk '{printf "      0x%sxx : %d ID(s)\n", $2, $1}'
}

echo
echo "================================ VERDICT =================================="

if [ "$have_expected" -eq 1 ]; then
  if [ "$miss0" -eq 0 ] && [ "$miss1" -eq 0 ]; then
    echo "  OK - every expected CAN ID is present on the bus it belongs to."
    exit 0
  fi
  if [ "$smiss0" -eq 0 ] && [ "$smiss1" -eq 0 ]; then
    echo "  REVERSED - the two USB-CAN adapters are on the wrong interfaces."
    echo "  All $((e0 + e1)) taxel IDs are transmitting; each server is just reading"
    echo "  the other harness. This is NOT a hardware fault."
    echo
    echo "  Fix:  ./reset_can.sh && ./setup_can.sh      (auto-detects and corrects)"
    exit 1
  fi
  # Genuinely absent: expected somewhere, seen on neither bus.
  cat "$WORK/seen0" "$WORK/seen1" | sort -u >"$WORK/seen_any"
  cat "$WORK/exp0" "$WORK/exp1" | sort -u >"$WORK/exp_any"
  comm -13 "$WORK/seen_any" "$WORK/exp_any" >"$WORK/absent"
  absent=$(count "$WORK/absent")
  if [ "$absent" -gt 0 ]; then
    echo "  HARDWARE - $absent expected ID(s) are absent from BOTH buses:"
    group_report "$WORK/absent"
    echo
    echo "  A whole 0xNxx group missing => that daisy-chain is unpowered or its"
    echo "  connector is loose. Scattered IDs => individual modules. Check the"
    echo "  ribbon connectors along that chain and re-run."
    echo
    echo "  Absent IDs: $(tr '\n' ' ' <"$WORK/absent")"
    exit 2
  fi
  echo "  PARTIAL - all IDs are present somewhere, but neither the as-wired nor"
  echo "  the swapped assignment is a clean match. Re-run with PROBE_SECS=3; if it"
  echo "  persists, the LEAP.xela map and the connected hardware disagree."
  exit 2
fi

# No server log to diff against - fall back to unique-ID counts.
echo "  (no xela_server startup log at $SERVER_LOG - using ID counts only)"
if [ "$n0" -eq "$EXPECTED_CAN0_IDS" ] && [ "$n1" -eq "$EXPECTED_CAN1_IDS" ]; then
  echo "  OK - $CAN0=$n0  $CAN1=$n1, as expected."
  exit 0
fi
if [ "$n0" -eq "$EXPECTED_CAN1_IDS" ] && [ "$n1" -eq "$EXPECTED_CAN0_IDS" ]; then
  echo "  REVERSED - $CAN0=$n0 and $CAN1=$n1 are the wrong way round."
  echo "  Fix:  ./reset_can.sh && ./setup_can.sh      (auto-detects and corrects)"
  exit 1
fi
echo "  UNEXPECTED - $CAN0=$n0 (want $EXPECTED_CAN0_IDS), $CAN1=$n1 (want $EXPECTED_CAN1_IDS)."
echo "  If a count is 0 the adapter or hand power is off; if it is low, part of a"
echo "  daisy-chain is silent. Start xela_server once so this script can diff"
echo "  against the full ID map, then re-run."
exit 2
