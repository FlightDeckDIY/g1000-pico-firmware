# Project Kickoff Prompt (New Repo)

## Objective
Create a new C/C++ firmware repo for the RP2350B G1000 device using the Raspberry Pi Pico SDK and TinyUSB. Replace MicroPython + USB CDC with a vendor-defined USB HID interface, preserving hardware pinouts and feature parity. Use ROM BOOTSEL + UF2 for firmware updates in V1.

## Inputs
- `prd.md` from the prior repo (copy into this repo first).
- Hardware pin mappings and MCP23017 configuration from the prior `config.py`.
- VID/PID: 0x2E8A / 0x10F7.

## Step 1: Repo Bootstrap
1. Initialize Pico SDK project structure (CMake + `pico_sdk_import.cmake`).
2. Add folders:
   - `src/app`, `src/config`, `src/hal`, `src/input`, `src/led`, `src/usb`, `src/protocol`.
3. Add `README.md` with build/flash steps and update workflow.
4. Add `AGENTS.md` (use the provided template).

## Step 2: Configuration and IDs
1. Create `src/config/pins.h` with all GPIO/I2C assignments matching `config.py`.
2. Create `src/protocol/protocol.h` with control IDs and HID report IDs per `prd.md`.
3. Define USB VID/PID and device strings in the TinyUSB descriptor.

## Step 3: Hardware Bring-Up
1. I2C init at 400 kHz on GPIO2/3.
2. MCP23017 init (input + pullups) and change tracking.
3. GPIO init for direct buttons and encoders.

## Step 4: Input Handling
1. Buttons: debounce, press/release/hold, MAP filtering, repeat for MAP direction.
2. Encoders: quadrature decode, single/dual detents, speed (1–5) for HDG/CRS/BARO.
3. Event queue / ring buffer for encoder interrupts.

## Step 5: USB HID
1. Implement HID input report `EVENT` and output reports `LED_CTL`, `SIM_STATUS`, `DEVICE_CTL`.
2. Add feature reports `DEVICE_INFO`, `PROTOCOL_INFO`.
3. Implement HID polling + safe reconnect handling.
4. CDC debug behind build flag (dev-only).

## Step 6: LED + Mode
1. PWM backlight with breathe/flash/steady.
2. Mode switching PFD/MFD with LED feedback.

## Step 7: Firmware Update
1. Implement `DEVICE_CTL` action to enter BOOTSEL (ROM USB boot).
2. Document Windows updater flow to copy UF2.

## Acceptance Targets
- HID device enumerates reliably on Windows.
- Windows app can read events and send output reports.
- All direct + MCP buttons/encoders function with correct speed reporting.
- LED behaviors match MicroPython.
- Firmware update works via Windows updater + UF2.
