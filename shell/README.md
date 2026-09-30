# XELA CAN bring-up

## Quick start

```bash
./setup_can.sh              # discover, attach, verify, self-correct
./run_xela_server_leap.sh   # terminal 1
./visulize_xela_leap.sh     # terminal 2
```

If taxels look dead in the visualizer, run `./check_xela_can.sh` **before** suspecting the
sensors. It is read-only and safe to run with the server live.

## The bus split

`etc_xela/xServ_leap.ini` declares `channel = can0,can1`, and `LEAP.xela` defines the whole
hand as one 26x31 / 368-taxel sensor split across those two buses:

| interface | taxels | pads | unique CAN IDs |
|---|---|---|---|
| `can0` | 296 | 4 fingertips (30 each) + 11 4x4 pads (16 each) | 296 |
| `can1` | 72 | 3 palm 4x6 pads (24 each) | 72 |

The unique-ID count is what makes the two harnesses distinguishable at bring-up.

## Never assume `/dev/ttyUSBn` ordering

`ttyUSBn` numbers come from kernel enumeration order, not from which physical port you used.
The two USB-CAN adapters sit at different USB topology depths and the LEAP hand's own FT232H
also claims a `ttyUSB` slot, so a reboot, a replug, or plugging things in a different order
silently swaps `can0` and `can1`.

When that happens the server is not broken and no sensor has failed — each bus reader is just
listening to the other harness. Symptom: a scattered subset of pads renders live (~54 CAN IDs
coincidentally overlap the other bus's map) while the rest render in `color_off` red. Swapping
the CAN connectors at the hand is *not* a reliable fix: that is a second, independent flip, and
doing one while the other also moved lands you back where you started.

`setup_can.sh` therefore binds adapters by FTDI serial through `/dev/serial/by-id`, then counts
the unique CAN IDs on each bus after bring-up and re-attaches them the other way round if they
came up reversed. It is correct regardless of enumeration order *and* of which connector is in
which adapter.

## `check_xela_can.sh`

Passive diagnostic. Per bus it reports the unique-ID count against expectation, the SocketCAN
error counters (`bus-errors`, `error-warn`, `bus-off`, `rx_dropped`), and — if `xela_server`
has been started at least once — a full diff against the ID map the server logs at startup in
`/etc/xela/LOG/xela_server.log`. Verdicts:

| verdict | exit | meaning |
|---|---|---|
| `OK` | 0 | every expected ID present on the bus it belongs to |
| `REVERSED` | 1 | wiring only — run `./reset_can.sh && ./setup_can.sh` |
| `HARDWARE` | 2 | IDs absent from **both** buses — a real fault |

For `HARDWARE`, missing IDs are grouped by leading nibble: a whole silent `0xNxx` group means
that daisy-chain is unpowered or its connector is loose; scattered IDs mean individual modules.

Use `PROBE_SECS=3` for a longer capture if counts look unstable.

## Other scripts

| script | purpose |
|---|---|
| `find_Xela_sensor_device_name.sh` | list the two USB-CAN adapters (FTDI `0403:6015`) by serial |
| `find_leapXela_USB.sh` | find the LEAP hand's Dynamixel bus (FTDI `0403:6014`) |
| `reset_can.sh` | tear down `can0`/`can1`/`vcan0`, kill `slcand`, unload modules |
| `downlload_binaries.sh` | fetch the XELA Suite AppImages into `linux_1.8.0_208601/` |

## Logs

`xela_server` redirects its logging to `/etc/xela/LOG/` shortly after startup. The repo-local
`shell/xelalib.log` and `shell/xela_error.log` only ever contain "Log File Changed" noise, and
`shell/linux_1.8.0_208601/xela_server.log` is a stale simulator run — none of the three are
useful for debugging. Use `/etc/xela/LOG/xela_server.log`.
