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
    from usb.device.hid import HIDInterface
except ImportError:
    usb = None
else:
    # 64-byte vendor-defined HID reports, one Input and one Output
    # report, sharing Report ID 1. The underlying transport will then
    # see 64-byte packets where byte 0 is the report ID and the
    # remaining bytes are payload (this matches how `protocol_binary`
    # builds its frames).
    _G1P_REPORT_DESC = (
        b"\x06\x00\xff"  # Usage Page (Vendor Defined 0xFF00)
        b"\x09\x01"      # Usage (Vendor Usage 1)
        b"\xa1\x01"      # Collection (Application)
        b"\x85\x01"      #   Report ID 1
        b"\x15\x00"      #   Logical Minimum (0)
        b"\x26\xff\x00"  #   Logical Maximum (255)
        b"\x75\x08"      #   Report Size (8 bits)
        b"\x95\x40"      #   Report Count (64 bytes) - Input
        b"\x09\x01"      #   Usage (Vendor Usage 1)
        b"\x81\x00"      #   Input (Data, Array, Absolute)
        b"\x85\x01"      #   Report ID 1 (Output)
        b"\x75\x08"      #   Report Size (8 bits)
        b"\x95\x40"      #   Report Count (64 bytes) - Output
        b"\x09\x01"      #   Usage (Vendor Usage 1)
        b"\x91\x00"      #   Output (Data, Array, Absolute)
        b"\xc0"          # End Collection
    )

    class G1PPanelHID(HIDInterface):
        """Simple vendor-defined HID interface for the G1000 panel.

        This defines a single 64-byte IN/OUT report with Report ID 1.
        Application code can later use `send_report()` and the
        `on_set_report()` hook to implement the full binary protocol.
        """

        def __init__(self):
            super().__init__(
                _G1P_REPORT_DESC,
                # Buffer for host->device OUT reports; 64 bytes matches
                # the report size in the descriptor above.
                set_report_buf=bytearray(64),
                # Non-boot, vendor-defined protocol.
                protocol=0x00,
                interface_str="G1000 FlightDeck HID",
            )

        def on_set_report(self, report_data, _report_id, _report_type):
            """Handle host->device OUT reports.

            For now, this is a placeholder that simply accepts the
            report. A future step will parse `report_data` using
            `protocol_binary.decode_report_to_message()` and route it
            through the CommandRouter.
            """
            # Always accept the report.
            return True

    # Instantiate and configure the runtime USB device using the
    # high-level usb.device helpers.
    _dev = usb.device.get()
    _dev.active(False)

    _iface = G1PPanelHID()

    # builtin_driver=True keeps the underlying CDC REPL/serial active
    # and appends this HID interface to the existing configuration.
    _dev.config(_iface, builtin_driver=True)
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
