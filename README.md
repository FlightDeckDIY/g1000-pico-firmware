# g1000-pico-firmware

This repository contains MicroPython firmware and helper scripts for the FlightDeckDIY G1000-style RP2350B project. Included in the repo is a custom UF2 MicroPython build that makes all 48 GPIOs of the RP2350B chip available to MicroPython.

## Included UF2 MicroPython build

- File: `fdd_g1p_rp2350b-firmware.uf2`

This is a custom MicroPython UF2 built for the RP2350B variant of the RP2 family. It exposes all 48 GPIOs (GPIO0 through GPIO47) to MicroPython so your project can use the full set of pins the RP2350B provides.

Notes and assumptions:
- The MicroPython Pin API is available as usual. GPIOs can be accessed using `machine.Pin(n)` where `n` is 0..47 (e.g. `Pin(0)`, `Pin(47)`). If you have a different pin naming convention in your toolchain, check the board's MicroPython port docs.
- This UF2 was created specifically for the hardware layout used in this project. If you try to use it on different RP2350B boards, verify pinout and flash at your own risk.

## Quickstart — Flashing the UF2

1. Put your RP2350B board into BOOTSEL / bootloader mode (usually by holding the BOOTSEL button while connecting USB — board-specific).
2. The board should mount as a USB mass storage device on your computer.
3. Copy `fdd_g1p_rp2350b-firmware.uf2` to the mounted storage. The board will flash and reboot into MicroPython.

After flashing, you can interact with the board using Thonny, rshell, mpremote, or any MicroPython tooling.

## Repository layout

- `main.py` — Project entrypoint. Runs on boot when using the provided UF2.
- `config.py` — Configuration values (pins, calibration, etc.).
- `mode_manager.py` — Handles mode switching logic for the device.
- `button_handler.py` — Button reading and debouncing logic.
- `encoder_handler.py` — Rotary encoder processing.
- `test_enhanced_encoders.py` — Tests for encoder behavior (unit-style test file—needs updating).
- `led_controller.py` — LED control helpers.
- `mcp23017_handler.py` — I/O expander (MCP23017) helper code — used for external I/O expanders in the hardware.
- `usb_comm.py` — USB communication helpers.
- `protocol_ids.py`, `protocol_binary.py` — USB HID protocol IDs and binary report encoding/decoding.
- `hid_transport.py` — USB HID transport (device side), used when HID is enabled.

If you add files or refactor, update this section so new contributors can find important bits quickly.

## Usage

- After booting, `main.py` will run automatically if present on the board's filesystem. Use Thonny or `mpremote` to open a REPL, inspect `config.py`, or run helper scripts interactively.
- Example to toggle a pin in the REPL:

```py
from machine import Pin
led = Pin(25, Pin.OUT)  # example; replace with the GPIO you want
led.toggle()
```

## Wiring and pin mapping

This README does not include a full pin map graphic. The custom UF2 exposes GPIO0..GPIO47. For the project's wiring and any mapping between board connectors and raw GPIO numbers, see `config.py` and the hardware documentation for your RP2350B board.

Recommended follow-ups (issues or pull requests):
- Add a pin mapping table that shows which physical connector pin maps to which GPIO number.
- Add wiring diagrams and photos of the assembled device.

## Troubleshooting

- If the board does not appear as a mass storage device when entering bootloader mode, check the board's BOOTSEL procedure and cable.
- If a pin does not behave as expected, verify you are using the correct GPIO number and that the UF2 you flashed is the custom RP2350B build included here.

### USB HID transport notes

- By default the firmware uses the existing CDC text protocol. The HID transport can be enabled in `main.py` by setting `USE_HID_TRANSPORT = True` in a HID-capable build.
- When HID is enabled, host→device commands are sent as 64-byte HID OUT reports encoded with `protocol_binary.encode_message_to_report`, and device→host responses and events (encoders/buttons) are sent as HID IN reports.
- See `protocol_ids.py` for message IDs and `protocol_binary.py` for the exact report layout.

## License & Contributing

This project is licensed under the MIT License — see the `LICENSE` file for full text.

Contributions are welcome. Please open issues or PRs to add wiring diagrams, tests, or to report problems with the included UF2 build.

## Contact

For questions about this repo or the UF2 build, open an issue in this repository.
