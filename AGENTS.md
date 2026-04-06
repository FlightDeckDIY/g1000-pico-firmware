# Repository Guidelines

## Project Structure & Module Organization
- Root-level Python modules implement the MicroPython firmware: `main.py` (entry point), `mode_manager.py`, `button_handler.py`, `encoder_handler.py`, `led_controller.py`, `mcp23017_handler.py`, and `usb_comm.py`.
- `config.py` holds pin mappings, calibration values, and project-specific constants; update this first when wiring changes.
- `fdd_g1000_1229251426` is the bundled UF2 firmware image for the RP2350B board.
- `README.md` documents flashing and usage; keep it in sync when adding modules or hardware assumptions.

## Build, Test, and Development Commands
This repo does not use a local build system; development is done by flashing UF2 and running MicroPython on-device.
- Flash UF2: copy `fdd_g1000_1229251426` to the RP2350B bootloader drive (BOOTSEL mode).
- REPL/dev tools (examples):
  - `mpremote connect /dev/tty.usbmodem* repl` — open a MicroPython REPL.
  - `mpremote connect /dev/tty.usbmodem* fs ls` — list files on the device.
  - `mpremote connect /dev/tty.usbmodem* fs put main.py` — update the entry point on the device.

## Coding Style & Naming Conventions
- Use 4-space indentation and standard Python/MicroPython conventions.
- Keep module names `snake_case.py` and prefer descriptive handler names (e.g., `*_handler.py`).
- Avoid heavy dependencies; favor lightweight, MicroPython-compatible patterns.

## Testing Guidelines
- No automated test harness is present. Validate changes by flashing the UF2 and exercising hardware flows.
- If you add tests, keep them runnable on-device and document how to invoke them in `README.md`.

## Commit & Pull Request Guidelines
- Commit messages in history are short, imperative, and focused (e.g., "Adjust manual brightness step value").
- Prefer one logical change per commit and include hardware impact in the message when relevant.
- PRs should include: a brief summary, hardware/board used, and any wiring or configuration changes.

## Configuration & Safety Notes
- Double-check GPIO numbers in `config.py` before flashing to avoid miswiring.
- This UF2 is board-specific; confirm pinout compatibility before use on other RP2350B boards.
