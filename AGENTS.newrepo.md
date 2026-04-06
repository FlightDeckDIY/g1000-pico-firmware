# Repository Guidelines (C/C++ Pico SDK)

## Project Structure & Module Organization
- `src/app/` holds the application entry point and main loop.
- `src/config/` contains pin mappings and build-time configuration headers.
- `src/hal/` contains hardware access (GPIO, I2C, MCP23017).
- `src/input/` contains button/encoder processing and debouncing.
- `src/led/` contains backlight control and effects.
- `src/usb/` contains TinyUSB HID (and optional CDC) implementation.
- `src/protocol/` contains HID report definitions and shared control IDs.
- `include/` contains public headers as needed.
- `boards/` or `pico_sdk_import.cmake` should be standard Pico SDK layout.
- `README.md` must reflect flashing, update workflow, and debug options.

## Build, Flash, and Development Commands
- Typical Pico SDK build:
  - `mkdir -p build && cd build`
  - `cmake ..`
  - `cmake --build .`
- UF2 flashing:
  - Copy the generated `.uf2` to the BOOTSEL drive.
- Debug (SWD): use the Pico debug probe + OpenOCD/GDB.
- USB CDC (debug only): controlled by a build flag; do not enable in production builds.

## Coding Style & Naming Conventions
- Use 4-space indentation for C/C++.
- Use `snake_case` for files and functions.
- Keep headers small and focused; prefer `static` for internal functions.
- Avoid heavy dependencies beyond Pico SDK/TinyUSB.

## Testing Guidelines
- No automated test harness is required initially.
- Validate on hardware: verify HID events, encoder speed, and LED behavior.
- Document any test steps or required host tools in `README.md`.

## Commit & Pull Request Guidelines
- Commit messages should be short, imperative, and focused.
- Prefer one logical change per commit; mention hardware impact if applicable.
- PRs should include: summary, board used, wiring/config changes, and test notes.

## Configuration & Safety Notes
- Hardware pinouts must match the existing MicroPython project.
- I2C addresses for MCP23017 must remain the same.
- Confirm VID/PID and HID report IDs before shipping.

## Firmware Update Policy
- V1 uses ROM BOOTSEL + UF2 updates via the Windows updater app.
- HID DFU is a future option (V2+) if mass-storage updates are blocked in target environments.
