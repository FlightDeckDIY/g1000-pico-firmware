"""HID transport for G1P Flight Display Device.

This module defines HIDTransport, which is responsible for:

* Polling USB HID OUT reports from the host, decoding them into
  messages via protocol_binary, and routing them through CommandRouter.
* Encoding any device->host messages (responses or async events) into
  HID IN reports and sending them.

The implementation is written to be defensive around the concrete
MicroPython HID API. It attempts to use common methods (``recv``,
``send``, ``send_report``, ``readinto``, ``write``) if they exist on the
HID device object, and otherwise degrades to a no-op so non-HID builds
or mismatched APIs do not crash the firmware.
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
    """USB HID transport.

    The public API is:
        - poll(): non-blocking processing of any pending host->device
          reports.
        - send_message_from_app(msg): send a device->host message as a
          HID IN report.

    If no HID device is available, all methods degrade to safe no-ops so
    that CDC-only builds continue to function.
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
                devices = getattr(usb_hid, "devices", [])
                # In many ports, usb_hid.devices is a list of Device
                # objects. Here we simply choose the first one, but this
                # can be refined to filter by usage page/usage or
                # VID/PID if needed.
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
        It performs non-blocking reads of OUT reports, decodes them into
        messages, routes them via CommandRouter, and sends any response
        messages back to the host.
        """
        if self._hid_device is None:
            # HID not available in this build; nothing to do.
            return

        while True:
            report = self._read_report_nonblocking()
            if report is None:
                break

            try:
                msg = decode_report_to_message(report)
            except Exception:
                msg = None

            if not msg:
                continue

            try:
                responses = self.command_router.handle_message(msg) or []
            except Exception:
                # Do not let application errors break the USB loop.
                continue

            for resp in responses:
                self.send_message_from_app(resp)

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
            report = encode_message_to_report(
                message, report_id=REPORT_ID_DEVICE_TO_HOST
            )
        except Exception:
            return

        dev = self._hid_device

        try:
            # Prefer a high-level HID API if available.
            if hasattr(dev, "send"):
                # pyb.USB_HID style
                dev.send(report)
            elif hasattr(dev, "send_report"):
                # Some ports expose a send_report() helper
                dev.send_report(report)
            elif hasattr(dev, "write"):
                # Generic stream-like API
                dev.write(report)
            else:
                # No known send method; do nothing.
                return
        except Exception:
            # Swallow transport errors; higher layers may choose to log.
            return

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _read_report_nonblocking(self):
        """Attempt to read one HID OUT report without blocking.

        Returns:
            ``bytes`` of length ``REPORT_SIZE``, or ``None`` if no
            report is available.
        """
        if self._hid_device is None:
            return None

        dev = self._hid_device

        # Try a few common MicroPython/CircuitPython-style APIs in a
        # defensive way. All failures degrade to "no data".
        try:
            # pyb.USB_HID style: recv(buffer, timeout=ms) -> nbytes
            if hasattr(dev, "recv"):
                buf = bytearray(self.report_size)
                n = dev.recv(buf, timeout=0)
                if not n:
                    return None
                if n < self.report_size:
                    # Zero-pad remaining bytes
                    for i in range(n, self.report_size):
                        buf[i] = 0
                return bytes(buf)

            # Stream-like: readinto(buf) -> nbytes
            if hasattr(dev, "readinto"):
                buf = bytearray(self.report_size)
                n = dev.readinto(buf)
                if not n:
                    return None
                if n < self.report_size:
                    for i in range(n, self.report_size):
                        buf[i] = 0
                return bytes(buf)

            # Simpler read(N) API
            if hasattr(dev, "read"):
                data = dev.read(self.report_size)
                if not data:
                    return None
                if len(data) < self.report_size:
                    buf = bytearray(self.report_size)
                    buf[: len(data)] = data
                    for i in range(len(data), self.report_size):
                        buf[i] = 0
                    return bytes(buf)
                return data
        except Exception:
            return None

        # No known read method.
        return None
