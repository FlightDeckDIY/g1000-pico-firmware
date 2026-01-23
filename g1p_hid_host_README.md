# g1p_hid_host.py — G1P HID Host Utility

This script is a simple host-side tool for talking to the G1P panel over USB HID.
It can:

- Open the G1P HID interface by VID/PID.
- Send a few basic commands (device info, encoder stats, etc.).
- Continuously print encoder and button events as they arrive.

## Requirements

- Python 3.8+
- The `hid` Python package (wrapper around hidapi)
- Access to `protocol_ids.py` and `protocol_binary.py` from this repo

### Install dependencies

From the repo root (or any directory where you plan to run the script):

```bash
pip install hid
```

Make sure the current working directory includes `protocol_ids.py` and
`protocol_binary.py` (running from the firmware repo root is easiest).

## Device identification

The script is preconfigured for the G1P HID interface:

- `VENDOR_ID = 0x2E8A`
- `PRODUCT_ID = 0x10F7`

If you change the HID descriptor or PID in the firmware, update these
constants in `g1p_hid_host.py` accordingly.

## Firmware-side setup

On the device, you need a HID-capable MicroPython build and the firmware
configured to use HID:

1. Flash the HID-capable UF2 to the board.
2. In `main.py`, set:

   ```python
   USE_HID_TRANSPORT = True
   ```

3. Copy the updated firmware files to the device and reboot.

When HID is enabled, CDC text I/O is no longer used for protocol commands;
all traffic goes over HID reports instead.

## Running the host script

From the firmware repo root (so the protocol modules are importable):

```bash
python g1p_hid_host.py
```

What it does:

1. Searches for a HID device with VID/PID `0x2E8A:0x10F7`.
2. Opens it in non-blocking mode.
3. Sends:
   - `MSG_DEVICE_INFO_REQUEST`
   - `MSG_ENCODER_STATS_REQUEST`
4. Enters a loop reading HID IN reports and printing decoded messages.

You should see lines like:

- `[DEVICE_INFO] uid=... type=... mode=PFD fw=0.1.1`
- `[ENCODER_EVENT] id=... dir=CW/CCW speed=N panel=PFD/MFD`
- `[BUTTON_EVENT] id=... type=PRESS/RELEASE/LONG_PRESS panel=...`

## Useful host commands

`g1p_hid_host.py` exposes a few helper functions you can call from an
interactive Python session if you want more control:

- `cmd_device_info(dev)` — request device info.
- `cmd_encoder_stats_request(dev)` — request encoder buffer stats.
- `cmd_encoder_stats_reset(dev)` — reset encoder stats.
- `cmd_sim_status(dev, connected: bool)` — set sim connected/disconnected.
- `cmd_led_mode(dev, mode)` — set LED mode (`LED_MODE_ON`, `LED_MODE_OFF`, etc.).
- `cmd_led_brightness(dev, brightness)` — set LED brightness (0–100).
- `cmd_electrical_master(dev, on: bool)` — toggle electrical master state.

In normal use, just running `python g1p_hid_host.py` is enough to verify
basic HID communication and watch live events.

## Troubleshooting

- If the script prints `G1P HID device not found`, check:
  - The board is connected and running the HID-enabled firmware.
  - `USE_HID_TRANSPORT` is set to `True` in `main.py`.
  - VID/PID in `g1p_hid_host.py` match the firmware's HID descriptor.
- If you see raw HID reports but no decoded messages, verify that the
  report layout and message IDs match those defined in `protocol_ids.py`
  and `protocol_binary.py` on both host and device.