# PRD: RP2350B C/C++ HID Firmware for FDD G1000 Device

## Summary
Build a new firmware project (new repo) for the RP2350B custom PCB using the Raspberry Pi Pico C/C++ SDK. Replace MicroPython + CDC serial with a vendor-defined USB HID interface to avoid COM port contention on Windows. Preserve hardware pinouts and feature parity with the existing MicroPython firmware, while improving latency and compatibility. Support firmware updates over USB via a Windows companion updater app.

## Problem Statement
The current MicroPython firmware communicates over USB CDC (COM port). On Windows, other software frequently locks the COM port, blocking the custom driver/application. The device needs a USB HID transport (vendor-defined) that avoids COM port contention while maintaining low latency and full feature parity.

## Goals (in priority order)
1. **Low latency** input events for encoders/buttons; HID polling should be sufficient for human input.
2. **Windows compatibility** without COM port contention by using vendor-defined HID.
3. **Feature parity** with the existing MicroPython behavior (input events, encoder speed, LED behavior, mode switching).

## Non-Goals
- Cross-platform host support (Windows only for now).
- Recreating the MicroPython REPL or dynamic scripting features.
- A full test harness (basic device-level validation only).

## Constraints
- **Hardware pinouts must remain unchanged** (same wiring and GPIO assignments as `config.py`).
- Use **RP2350B** custom PCB with MCP23017 I/O expanders.
- Use **TinyUSB** (via Pico SDK) for USB.
- Must support **USB-based firmware updates** without Pico tooling on the user’s PC.
- USB VID/PID fixed for this device: **VID 0x2E8A**, **PID 0x10F7**.

## Success Criteria
- Median input-to-host event latency feels instantaneous for users (target: <10 ms end-to-end).
- Windows app can always connect (no COM port contention issues).
- All current button/encoder/LED behaviors are preserved.

## Current Feature Snapshot (MicroPython)
- Direct MCU buttons and encoders (interrupt-driven + fallback polling).
- MCP23017 expanders for additional buttons/encoders.
- Encoder detent handling with speed calculation (1–5) for specific encoders.
- Mode switching (PFD/MFD) with LED feedback.
- LED backlight with breathing, flashing, and brightness control.
- USB command handling for device info, LED control, sim status, etc.

## Proposed Firmware Architecture (C/C++ Pico SDK)
**High-level modules** (names are suggestions):
- `src/app/main.c` – main loop, scheduler, timing.
- `src/config/pins.h` – pin mappings (mirrors `config.py`).
- `src/hal/gpio.c` – direct buttons/encoders.
- `src/hal/i2c_mcp23017.c` – MCP23017 init + change tracking.
- `src/input/buttons.c` – debouncing, long-press, MAP button filtering.
- `src/input/encoders.c` – quadrature decoding, speed calculation, interrupt buffering.
- `src/mode/mode.c` – PFD/MFD logic.
- `src/led/led.c` – backlight, breathing/flash patterns.
- `src/usb/usb_hid.c` – HID reports, protocol parsing.
- `src/usb/usb_cdc.c` – optional debug logging.
- `src/usb/protocol.h` – message/report definitions.

**Core loop**
- Use repeating timers for consistent cadence: 1 ms encoder check, 1 ms MCP scan, 10 ms LED updates, 5 ms USB service (as reference from current firmware).
- Direct encoder interrupts push to a ring buffer; processing happens in the main loop.

## USB HID Design
### Device Type
- Vendor-defined HID interface (Windows HID, no custom driver required).
- Optional composite device: HID + CDC (**dev-only**, controlled by build flag).

### HID Report Model (fixed for V1)
- **Input Reports** (device -> host):
  - `EVENT` report (ID 0x01): button, encoder, backlight, mode, status.
- **Output Reports** (host -> device):
  - `LED_CTL` report (ID 0x10): brightness, breathing, flash, steady.
  - `SIM_STATUS` report (ID 0x11): connected/disconnected.
  - `DEVICE_CTL` report (ID 0x12): reset, request info, enter bootloader.
- **Feature Reports** (host <-> device):
  - `DEVICE_INFO` report (ID 0x20): firmware version, device ID, board info.
  - `PROTOCOL_INFO` report (ID 0x21): protocol version and capabilities.

### Event Payload Fields
- `event_type`: button / encoder / backlight / mode / status
- `control_id`: enumerated ID for each button/encoder (derived from names in `config.py`)
- `value`: press/release/hold, direction, brightness, etc. (int8)
- `speed`: encoder velocity (1–5) where applicable
- `mode`: PFD or MFD
- `seq`: rolling sequence counter for host-side gap detection

### HID Payload Size
- Fixed report size: 32 bytes (fits full-speed HID, leaves room for growth).

### Host App Changes (Windows)
- Update to use HID API (e.g., HidD/HidP or HIDAPI).
- Implement new protocol parser for reports.
- Optional: provide a compatibility mode to translate HID events into existing command handling.

## Firmware Update Strategy (USB)
**Required:** User must update firmware via Windows app without Pico tools.

**Decision for V1 (Option A): ROM boot + UF2**
- Use Pico SDK `reset_usb_boot` (or RP2350B equivalent) to reboot into ROM bootloader (USB mass storage).
- Windows updater app detects BOOTSEL drive and copies a UF2 firmware file.
- Advantages: simple, robust, no custom bootloader needed.
- Validation task: confirm RP2350B supports ROM USB boot jump and UF2 copy workflow.

**Fallback (Option B, V2 if needed):** HID-based firmware update
- Implement HID-based firmware update (custom bootloader or TinyUSB DFU runtime).
- Advantages: fully in-app update, no drive mounting.
- Risk: higher complexity, more QA.

## Detailed Functional Requirements
### Input Handling
- **Buttons (direct + MCP):**
  - Debounce, press/release events, long-press detection.
  - MAP button filtering (suppress MAP_PUSH when direction buttons are active).
  - Repeat behavior for MAP direction buttons after delay.
- **Encoders (direct + MCP):**
  - Quadrature decoding with full transition validation.
  - Single vs dual detent support.
  - Velocity (speed 1–5) for HDG and CRS/BARO encoders (feature parity).
- **Event Emission:**
  - Publish events via HID input reports with consistent IDs.

### LED / Backlight
- Support brightness, breathe, flash, steady modes.
- Backlight encoder should adjust brightness with step size equivalent to `NAV_VOL_BRIGHTNESS_STEP`.

### Mode Switching
- Maintain PFD/MFD mode logic and LED feedback on mode changes.

### USB / Protocol
- Robust to host disconnects and reconnects.
- Avoid blocking behavior in USB callbacks.

## Hardware Mapping (from `config.py`)
### Direct MCU Buttons
- NAV_VOL_PUSH (GPIO4)
- NAV_SWAP (GPIO7)
- NAV_FQ_PUSH (GPIO12)
- HDG_SYNC (GPIO13)
- AP_TOGGLE (GPIO16)
- AP_FD_TOGGLE (GPIO17)
- AP_HDG_HOLD (GPIO18)
- AP_ALT_HOLD (GPIO19)
- AP_NAV_HOLD (GPIO20)
- AP_VNV (GPIO33)
- AP_BC (GPIO34)
- AP_APR (GPIO35)
- AP_VS_HOLD (GPIO36)
- AP_NOSE_UP (GPIO37)
- AP_NOSE_DOWN (GPIO38)
- AP_FLC (GPIO39)
- ALT_SYNC (GPIO44)

### Direct MCU Encoders
- NAV_VOL (GPIO5, GPIO6) – single detent
- NAV_FQ_MINOR (GPIO8, GPIO10) – dual detent
- NAV_FQ_MAJOR (GPIO9, GPIO11) – dual detent
- HDG_BUG (GPIO14, GPIO15) – single detent
- ALT_MINOR (GPIO40, GPIO41) – dual detent
- ALT_MAJOR (GPIO42, GPIO43) – dual detent

### MCP23017 Addresses
- BOTTOM: 0x20
- RIGHT_LOWER: 0x22
- RIGHT_UPPER: 0x24

### I2C
- SDA GPIO2, SCL GPIO3, 400 kHz
- MCP interrupt pin: GPIO1

## Performance Targets
- Input event to HID report queued within 1–5 ms typical.
- HID polling interval configurable (target 1–2 ms if feasible).

## Risks & Mitigations
- **RP2350B ROM boot behavior unknown**: validate early; fallback to custom bootloader if needed.
- **Composite USB complexity**: keep CDC debug behind a build flag; ship HID-only by default.
- **MCP23017 latency**: use interrupt-driven change detection + fast read of INTCAP/GPx.

## Milestones (Suggested)
1. **Repo bootstrap**: Pico SDK project skeleton, pin config header, I2C + GPIO init.
2. **Input parity**: direct buttons/encoders + MCP23017 with debouncing and speed.
3. **USB HID**: vendor-defined HID reports + Windows app integration stub.
4. **LED + mode**: breathing/flash/backlight parity.
5. **Firmware update path**: implement ROM boot + UF2; validate on RP2350B.
6. **Stability pass**: soak testing, overflow handling, reconnect behavior.

## Open Questions
- Confirm RP2350B supports `reset_usb_boot` (or equivalent) and Windows UF2 copy workflow.
- Any additional controls planned beyond those in `config.py`?
- CDC debug remains dev-only; confirm if any field diagnostics need to ship in production builds.

## Decision Rationale: Update Path
- **V1 uses ROM BOOTSEL + UF2** to minimize firmware complexity and speed delivery while preserving a robust recovery path.
- **HID DFU deferred to V2** unless Windows mass-storage policies block UF2 updates in target environments.

## Acceptance Checklist
- HID device enumerates reliably on Windows.
- Windows app can read input reports and send output reports.
- All direct and MCP buttons/encoders generate correct events.
- LED behaviors and brightness control match current firmware.
- Firmware update works from a Windows companion tool without Pico tooling.

## Appendix A: HID Protocol Spec (Draft V1)
### A1. Report IDs and Sizes
- 0x01 `EVENT` (Input) – 32 bytes
- 0x10 `LED_CTL` (Output) – 32 bytes
- 0x11 `SIM_STATUS` (Output) – 32 bytes
- 0x12 `DEVICE_CTL` (Output) – 32 bytes
- 0x20 `DEVICE_INFO` (Feature) – 32 bytes
- 0x21 `PROTOCOL_INFO` (Feature) – 32 bytes

### A2. Common Conventions
- Little-endian for multi-byte fields.
- `seq` increments per event and wraps at 255.
- `mode`: 0 = PFD, 1 = MFD.
- `event_type`:
  - 0x01 = BUTTON
  - 0x02 = ENCODER
  - 0x03 = BACKLIGHT
  - 0x04 = MODE
  - 0x05 = STATUS
- `button_action` (for BUTTON events in `value`):
  - 0 = RELEASE
  - 1 = PRESS
  - 2 = HOLD
  - 3 = LONG_PRESS
  - 4 = REPEAT

### A3. Input Report: EVENT (0x01, 32 bytes)
```
byte 0  report_id      = 0x01
byte 1  seq            = rolling sequence
byte 2  event_type     = enum (A2)
byte 3  flags          = reserved for future (0 for now)
byte 4  control_id_lo
byte 5  control_id_hi
byte 6  value          = int8 (button_action or encoder dir or mode)
byte 7  speed          = uint8 (1-5 for encoder, else 0)
byte 8  mode           = uint8 (0=PFD, 1=MFD)
byte 9  tick_lo        = uint16 ms tick (LSB)
byte 10 tick_hi
byte 11..31 reserved   = 0
```

Event notes:
- BUTTON: `value` uses button_action enum; `speed=0`.
- ENCODER: `value` = +1 (CW) or -1 (CCW), `speed` = 1–5.
- BACKLIGHT: `control_id` = NAV_VOL encoder; `value` = signed delta (steps).
- MODE: `value` = 0 (PFD) or 1 (MFD).
- STATUS: `value` = 0 (disconnected) or 1 (connected).

### A4. Output Report: LED_CTL (0x10, 32 bytes)
```
byte 0  report_id      = 0x10
byte 1  effect         = 0=OFF, 1=STEADY, 2=BREATH, 3=FLASH
byte 2  brightness     = 0..100 (ignored for FLASH unless overridden)
byte 3  param0         = effect-specific (see below)
byte 4  param1_lo
byte 5  param1_hi
byte 6  param2         = effect-specific
byte 7..31 reserved    = 0
```
Effect parameters:
- STEADY: brightness applied immediately; params ignored.
- BREATH: param0 = min_brightness (0..100), param1 = duration_ms (uint16), param2 = max_brightness (0..100).
- FLASH: param0 = flash_count (0 = continuous), param1 = period_ms (uint16), param2 = flash_brightness (0..100).

### A5. Output Report: SIM_STATUS (0x11, 32 bytes)
```
byte 0  report_id      = 0x11
byte 1  connected      = 0 or 1
byte 2..31 reserved    = 0
```

### A6. Output Report: DEVICE_CTL (0x12, 32 bytes)
```
byte 0  report_id      = 0x12
byte 1  action         = 0=NOP, 1=RESET, 2=ENTER_BOOT, 3=REQUEST_INFO
byte 2  mode           = 0=PFD, 1=MFD, 2=NO_CHANGE
byte 3..31 reserved    = 0
```

### A7. Feature Report: DEVICE_INFO (0x20, 32 bytes)
```
byte 0  report_id      = 0x20
byte 1  proto_major
byte 2  proto_minor
byte 3  fw_major
byte 4  fw_minor
byte 5  fw_patch
byte 6  board_id       = 0x01 (RP2350B custom)
byte 7  usb_vid_lo
byte 8  usb_vid_hi
byte 9  usb_pid_lo
byte 10 usb_pid_hi
byte 11..18 device_id  = 8 bytes of unique ID
byte 19..31 reserved   = 0
```
Device USB IDs (V1): VID 0x2E8A, PID 0x10F7.

### A8. Feature Report: PROTOCOL_INFO (0x21, 32 bytes)
```
byte 0  report_id      = 0x21
byte 1  proto_major
byte 2  proto_minor
byte 3  flags          = bit0: CDC present, bit1: boot_cmd supported
byte 4..31 reserved    = 0
```

### A9. Control IDs (control_id uint16)
The Windows app and firmware share a generated header (`protocol.h`) that enumerates IDs. Suggested mapping:

**Direct MCU Buttons**
1  NAV_VOL_PUSH
2  NAV_SWAP
3  NAV_FQ_PUSH
4  HDG_SYNC
5  AP_TOGGLE
6  AP_FD_TOGGLE
7  AP_HDG_HOLD
8  AP_ALT_HOLD
9  AP_NAV_HOLD
10 AP_VNV
11 AP_BC
12 AP_APR
13 AP_VS_HOLD
14 AP_NOSE_UP
15 AP_NOSE_DOWN
16 AP_FLC
17 ALT_SYNC

**Direct MCU Encoders**
101 NAV_VOL
102 NAV_FQ_MINOR
103 NAV_FQ_MAJOR
104 HDG_BUG
105 ALT_MINOR
106 ALT_MAJOR

**MCP Buttons (BOTTOM)**
201 SK1
202 SK2
203 SK3
204 SK4
205 SK5
206 SK6
207 SK7
208 SK8
209 SK9
210 SK10
211 SK11
212 SK12

**MCP Buttons (RIGHT_LOWER)**
301 CLR
302 FPL
303 DIRECT_TO
304 CRS_BARO_PUSH
305 MENU
306 PROC
307 ENT
308 FMS_PUSH

**MCP Buttons (RIGHT_UPPER)**
401 MAP_RIGHT
402 MAP_UP
403 MAP_LEFT
404 MAP_DOWN
405 MAP_PUSH
406 COM_SWAP
407 COM_FQ_PUSH
408 COM_VOL_PUSH

**MCP Encoders**
501 CRS_BARO_MINOR
502 CRS_BARO_MAJOR
503 FMS_MINOR
504 FMS_MAJOR
505 COM_FQ_MINOR
506 COM_FQ_MAJOR
507 COM_VOL
508 MAP

Reserved ranges:
- 600–699: future buttons
- 700–799: future encoders
- 800–899: status/system
