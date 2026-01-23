"""Runtime HID interface glue for the G1P Flight Deck device.

This module defines a singleton HID interface that:

- Exposes a 64-byte vendor-defined HID IN/OUT report (Report ID 1),
  matching the layout used in protocol_binary.py.
- Buffers host->device OUT reports received via on_set_report().
- Provides a process_pending(command_router) helper that decodes
  buffered reports into messages, routes them through CommandRouter,
  and sends any responses back to the host as HID IN reports.

It is designed to be instantiated from boot.py (so the HID interface is
present at USB enumeration time) and then driven from main.py by calling
process_pending() periodically from the main loop.
"""

try:
    import usb.device
    from usb.device.hid import HIDInterface
except ImportError:  # Not a HID-capable build
    HIDInterface = None  # type: ignore

from protocol_binary import (
    encode_message_to_report,
    decode_report_to_message,
    REPORT_ID_DEVICE_TO_HOST,
    REPORT_SIZE,
)

# 64-byte vendor-defined HID reports, one Input and one Output report,
# sharing Report ID 1. This matches the host-side expectations in
# g1p_hid_host.py and the internal layout in protocol_binary.py.
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


class _NullHIDInterface:
    """No-op stand-in used when HID is not available.

    This lets main.py import panel_hid unconditionally and simply have
    process_pending() be a no-op on non-HID builds.
    """

    def process_pending(self, command_router):  # pragma: no cover - trivial
        return


if HIDInterface is None:
    # Not a HID-capable build; expose a dummy interface so imports work.
    panel_hid = _NullHIDInterface()
else:

    class G1PPanelHID(HIDInterface):
        """Vendor-defined HID interface for the G1000 panel.

        - Single 64-byte IN/OUT report with Report ID 1.
        - Buffers OUT reports and lets application code process them via
          process_pending(command_router).
        """

        def __init__(self):
            super().__init__(
                _G1P_REPORT_DESC,
                # Buffer for host->device OUT reports; 64 bytes matches
                # the report size in the descriptor above.
                set_report_buf=bytearray(REPORT_SIZE),
                # Non-boot, vendor-defined protocol.
                protocol=0x00,
                interface_str="G1000 FlightDeck HID",
            )
            self._pending = []  # list of bytes objects, each REPORT_SIZE long

        # ------------------------------------------------------------------
        # HID callbacks
        # ------------------------------------------------------------------
        def on_set_report(self, report_data, _report_id, _report_type):
            """Handle host->device OUT reports.

            We copy the raw data into a fixed-size REPORT_SIZE buffer and
            append it to the pending queue for processing in the main
            loop.
            """
            # Ensure we always work with exactly REPORT_SIZE bytes.
            data = bytes(report_data)
            if len(data) < REPORT_SIZE:
                buf = bytearray(REPORT_SIZE)
                buf[: len(data)] = data
                data = bytes(buf)
            elif len(data) > REPORT_SIZE:
                data = data[:REPORT_SIZE]

            self._pending.append(data)
            # Always accept the report.
            return True

        # ------------------------------------------------------------------
        # Application-facing API
        # ------------------------------------------------------------------
        def process_pending(self, command_router):
            """Decode and route any pending host->device reports.

            For each decoded message, we call command_router.handle_message()
            and then emit any responses back to the host as HID IN reports.
            """
            if not self._pending or command_router is None:
                return

            # Local copy of queue to minimise time spent with a growing list.
            pending = self._pending
            self._pending = []

            for report in pending:
                try:
                    msg = decode_report_to_message(report)
                except Exception:
                    msg = None
                if not msg:
                    continue

                try:
                    responses = command_router.handle_message(msg) or []
                except Exception:
                    continue

                for resp in responses:
                    try:
                        out_rep = encode_message_to_report(
                            resp, report_id=REPORT_ID_DEVICE_TO_HOST
                        )
                        # HIDInterface provides send_report() for IN data.
                        self.send_report(out_rep)
                    except Exception:
                        # Ignore individual response errors to keep the
                        # transport robust.
                        continue

    # Singleton instance used by boot.py and main.py
    panel_hid = G1PPanelHID()
