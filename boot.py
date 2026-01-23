"""boot.py for FLIGHT_DECK_RP2350B_G1000_HID

Executed before `main.py` and before the USB subsystem is fully
initialised. This is where we configure a runtime USB HID interface
using the new MicroPython USB stack.

Design goals
------------
- Enumerate as a **USB HID class device** (vendor-defined usage page).
- Keep the built-in USB CDC serial interface (so REPL and existing CDC
  protocol keep working) when possible.
- Fall back cleanly on builds that do **not** have the high-level
  `usb.device` helpers available.

Runtime behaviour
-----------------
On firmware builds that include the micropython-lib USB packages
(`usb-device` and `usb-device-hid`):

- We create a custom HID interface using `usb.device.hid.HIDInterface`,
  with 64-byte IN and OUT reports (suitable for the existing
  `protocol_binary` layout).
- We initialise the runtime USB device via `usb.device.get().config(...)`
  with `builtin_driver=True` so the built-in CDC interface is preserved.

On builds without those helpers:

- We fall back to selecting the built-in USB configuration only, using
  `machine.USBDevice`, which keeps the device behaving as a pure CDC
  serial device.

This keeps the firmware robust while allowing a HID-capable build to
expose a real HID interface immediately at boot.
"""

# ---------------------------------------------------------------------------
# Preferred path: use micropython-lib usb-device-hid (if available)
# ---------------------------------------------------------------------------

try:
    import usb.device
except ImportError:
    usb = None
else:
    # Use the shared HID interface singleton defined in g1p_hid_runtime.
    from g1p_hid_runtime import panel_hid

    # Instantiate and configure the runtime USB device using the
    # high-level usb.device helpers.
    _dev = usb.device.get()
    _dev.active(False)

    # builtin_driver=True keeps the underlying CDC REPL/serial active
    # and appends this HID interface to the existing configuration.
    _dev.config(panel_hid, builtin_driver=True)
    _dev.active(True)


# ---------------------------------------------------------------------------
# Fallback path: only built-in USB configuration via machine.USBDevice
# ---------------------------------------------------------------------------

if "usb" not in globals() or usb is None:
    try:
        from machine import USBDevice
    except ImportError:
        # Firmware was built without runtime USB support at all.
        raise SystemExit

    dev = USBDevice()

    try:
        dev.active(False)
    except Exception:
        pass

    try:
        dev.builtin_driver = USBDevice.BUILTIN_DEFAULT
    except Exception:
        dev.builtin_driver = USBDevice.BUILTIN_NONE

    base = dev.builtin_driver

    try:
        desc_dev = base.desc_dev
        desc_cfg = base.desc_cfg
    except AttributeError:
        raise SystemExit

    dev.config(desc_dev, desc_cfg)
    dev.active(True)
