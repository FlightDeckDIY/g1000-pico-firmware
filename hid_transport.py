"""HID transport for G1P Flight Display Device (stub implementation).

This module defines HIDTransport, which is responsible for:

* Polling USB HID OUT reports from the host, decoding them into
  messages via protocol_binary, and routing them through CommandRouter.
* Encoding any device->host messages (responses or async events) into
  HID IN reports and sending them.

At this stage, the actual USB HID I/O is deliberately left as a stub so
that the rest of the firmware can be developed and tested without a
custom MicroPython build. Once a HID-capable build is available, you
can wire in the concrete API (e.g., usb_hid.Device or a TinyUSB binding)
inside the _read_report() and _write_report() methods.
"""

try:
    import usb_hid  # type: ignore
except ImportError:  # Running on a build without HID support
    usb_hid = None

from protocol_binary import (
    encode_message_to_report,
    decode_report_to_message,
    REPORT_ID_HOST_TO_DEVICE,
    REPORT_ID_DEVICE_TO_HOST,
    REPORT_SIZE,
)


class HIDTransport:
    """Stub HID transport.

    The public API is stable:
        - poll(): non-blocking processing of any pending host->device
          reports.
        - send_message_from_app(msg): enqueue a device->host message to
          be sent as a HID IN report.

    Until HID I/O is wired up, these methods act as no-ops if usb_hid is
    not available.
    """

    def __init__(self, command_router, report_size=REPORT_SIZE):
        self.command_router = command_router
        self.report_size = report_size
        self._hid_device = None

        # If usb_hid is available, select a device/interface here. The
        # concrete selection depends on how the HID interface is defined
        # in the custom MicroPython build.
        if usb_hid is not None:
            try:
                # Placeholder: pick the first HID device. In a real
                # implementation you would filter by usage page/usage
                # or VID/PID.
                devices = getattr(usb_hid, "devices", [])
                if devices:
                    self._hid_device = devices[0]
            except Exception:
                self._hid_device = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def poll(self):
        """Process any pending host->device HID OUT reports.

        This is intended to be called frequently from the main loop.
        In a real implementation, this would perform a non-blocking
        read of one or more OUT reports, decode them into messages, and
        route them via CommandRouter.
        """
        if self._hid_device is None:
            # HID not available in this build; nothing to do.
            return

        # NOTE: The exact MicroPython usb_hid API may differ depending
        # on your custom build. The code below is intentionally left as
        # pseudocode to avoid breaking non-HID builds.
        #
        # Example shape (to be adapted):
        #   while True:
        #       report = self._read_report_nonblocking()
        #       if report is None:
        #           break
        #       msg = decode_report_to_message(report)
        #       if msg is None:
        #           continue
        #       responses = self.command_router.handle_message(msg) or []
        #       for resp in responses:
        #           self.send_message_from_app(resp)
        pass

    def send_message_from_app(self, message):
        """Send a device->host message as a HID IN report.

        This is intended to be called by the application layer when it
        wants to push encoder/button events or other async messages to
        the host. The message dict should follow the same schema used by
        CommandRouter and protocol adapters.
        """
        if self._hid_device is None:
            return

        try:
            report = encode_message_to_report(message, report_id=REPORT_ID_DEVICE_TO_HOST)
        except Exception:
            return

        # Pseudocode: actual send depends on your HID API.
        # For example, if the device exposes a send_report() method:
        #   try:
        #       self._hid_device.send_report(report)
        #   except Exception:
        #       pass
        pass

    # ------------------------------------------------------------------
    # Internal helpers (to be implemented with real HID API)
    # ------------------------------------------------------------------
    def _read_report_nonblocking(self):
        """Attempt to read one HID OUT report without blocking.

        Returns:
            bytes of length REPORT_SIZE, or None if no report is
            available. This is intentionally left as a stub; implement
            using your custom usb_hid API.
        """
        return None
