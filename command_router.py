"""Command routing for G1P Flight Display Device.

This module defines a CommandRouter that takes high-level message
objects (type + payload) and applies them to the application layer
(mode_manager, led_controller, encoder_handler, etc.), returning
optional response messages.

Messages are simple dicts of the form:
    {"type": MSG_*, "payload": {...}}

This layer is transport-agnostic: it does not know whether messages
came from CDC, HID, or anything else, and it does not print or handle
raw bytes. That work is done by adapters/transports.
"""

import machine
from binascii import hexlify

from protocol_ids import (
    # Message types
    MSG_DEVICE_INFO_REQUEST,
    MSG_RESET_REQUEST,
    MSG_SIM_STATUS_UPDATE,
    MSG_LED_MODE_SET,
    MSG_LED_BRIGHTNESS_SET,
    MSG_ELECTRICAL_MASTER_SET,
    MSG_ENCODER_STATS_REQUEST,
    MSG_ENCODER_STATS_RESET,
    MSG_DEVICE_INFO_RESPONSE,
    MSG_ENCODER_STATS_RESPONSE,
    # Modes / enums
    PANEL_MODE_PFD,
    PANEL_MODE_MFD,
    SIM_STATUS_CONNECTED,
    LED_MODE_OFF,
    LED_MODE_ON,
    LED_MODE_FLASH,
    LED_MODE_BREATHE,
    LED_MODE_STEADY,
    ELECTRICAL_MASTER_OFF,
    ELECTRICAL_MASTER_ON,
    DEVICE_TYPE_FDD_G1P_REV1,
)


class CommandRouter:
    """Routes protocol messages to application behavior.

    The router holds references to the main application components. It
    performs side effects (changing LED state, mode, encoder stats,
    scheduling reset) and returns a list of zero or more response
    messages that transports/adapters can encode and send back to the
    host.
    """

    def __init__(self, mode_manager, led_controller, encoder_handler,
                 set_sim_connected_cb, request_reset_cb,
                 firmware_version="0.1.1"):
        self.mode_manager = mode_manager
        self.led_controller = led_controller
        self.encoder_handler = encoder_handler
        self.set_sim_connected_cb = set_sim_connected_cb
        self.request_reset_cb = request_reset_cb
        self.firmware_version = firmware_version

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle_message(self, message):
        """Handle a single incoming message.

        Args:
            message: dict with keys "type" and "payload" (dict or None).

        Returns:
            List of response message dicts.
        """
        msg_type = message.get("type")
        payload = message.get("payload") or {}

        if msg_type == MSG_DEVICE_INFO_REQUEST:
            return [self._handle_device_info_request()]

        if msg_type == MSG_RESET_REQUEST:
            self._handle_reset_request(payload)
            return []

        if msg_type == MSG_SIM_STATUS_UPDATE:
            self._handle_sim_status_update(payload)
            return []

        if msg_type == MSG_LED_MODE_SET:
            self._handle_led_mode_set(payload)
            return []

        if msg_type == MSG_LED_BRIGHTNESS_SET:
            self._handle_led_brightness_set(payload)
            return []

        if msg_type == MSG_ELECTRICAL_MASTER_SET:
            self._handle_electrical_master_set(payload)
            return []

        if msg_type == MSG_ENCODER_STATS_REQUEST:
            return [self._handle_encoder_stats_request()]

        if msg_type == MSG_ENCODER_STATS_RESET:
            self._handle_encoder_stats_reset()
            return []

        # Unknown / unsupported message type: ignore for now.
        return []

    # ------------------------------------------------------------------
    # Handlers for specific commands
    # ------------------------------------------------------------------
    def _handle_device_info_request(self):
        """Build a DEVICE_INFO_RESPONSE message.

        This mirrors the information currently printed by the
        "deviceInfo" command: unique ID, device type/revision,
        firmware version, and current mode.
        """
        uid = hexlify(machine.unique_id()).decode("utf-8")

        mode = PANEL_MODE_PFD if (self.mode_manager and
                                  self.mode_manager.mode == PANEL_MODE_PFD) else PANEL_MODE_MFD

        # Parse firmware version string "major.minor.patch"
        major, minor, patch = 0, 0, 0
        try:
            parts = self.firmware_version.split(".")
            if len(parts) >= 1:
                major = int(parts[0])
            if len(parts) >= 2:
                minor = int(parts[1])
            if len(parts) >= 3:
                patch = int(parts[2])
        except Exception:
            # Fallback to zeros if parsing fails
            major, minor, patch = 0, 0, 0

        return {
            "type": MSG_DEVICE_INFO_RESPONSE,
            "payload": {
                "protocol_version": 1,
                "device_type": DEVICE_TYPE_FDD_G1P_REV1,
                "mode": mode,
                "fw_major": major,
                "fw_minor": minor,
                "fw_patch": patch,
                "unique_id": uid,
            },
        }

    def _handle_reset_request(self, payload):
        # Schedule a reset using the callback provided by main.py.
        if self.request_reset_cb:
            self.request_reset_cb()

    def _handle_sim_status_update(self, payload):
        status = payload.get("status", SIM_STATUS_CONNECTED)
        is_connected = (status == SIM_STATUS_CONNECTED)

        # Let the main application update its state and LED behavior.
        if self.set_sim_connected_cb:
            self.set_sim_connected_cb(is_connected)

    def _handle_led_mode_set(self, payload):
        if not self.led_controller:
            return

        mode = payload.get("mode", LED_MODE_ON)

        try:
            if mode == LED_MODE_OFF:
                self.led_controller.enabled = False
            elif mode == LED_MODE_ON or mode == LED_MODE_STEADY:
                self.led_controller.enabled = True
                self.led_controller.stop_breathing()
            elif mode == LED_MODE_FLASH:
                # Use a generic flash pattern; host can refine in the future.
                self.led_controller.flash()
            elif mode == LED_MODE_BREATHE:
                self.led_controller.enabled = True
                self.led_controller.start_breathing()
        except Exception:
            # Any exceptions should be logged by the caller/transport
            # if desired; the router stays silent.
            return

    def _handle_led_brightness_set(self, payload):
        if not self.led_controller:
            return

        brightness = payload.get("brightness", 0)
        try:
            # Clamp brightness 0-100
            if brightness < 0:
                brightness = 0
            elif brightness > 100:
                brightness = 100
            self.led_controller.brightness = brightness
        except Exception:
            return

    def _handle_electrical_master_set(self, payload):
        if not self.led_controller:
            return

        state = payload.get("state", ELECTRICAL_MASTER_OFF)
        try:
            if state == ELECTRICAL_MASTER_OFF:
                # Mirror existing behavior: start breathing when off.
                self.led_controller.start_breathing()
            elif state == ELECTRICAL_MASTER_ON:
                # Stop breathing when on.
                self.led_controller.stop_breathing()
        except Exception:
            return

    def _handle_encoder_stats_request(self):
        """Build an ENCODER_STATS_RESPONSE message from encoder_handler."""
        if not self.encoder_handler:
            # No handler available – respond with empty stats.
            return {
                "type": MSG_ENCODER_STATS_RESPONSE,
                "payload": {
                    "buffer_size": 0,
                    "buffer_capacity": 0,
                    "buffer_overflows": 0,
                    "encoders": {},
                },
            }

        stats = self.encoder_handler.get_encoder_stats()
        return {
            "type": MSG_ENCODER_STATS_RESPONSE,
            "payload": stats,
        }

    def _handle_encoder_stats_reset(self):
        if self.encoder_handler:
            self.encoder_handler.reset_stats()
