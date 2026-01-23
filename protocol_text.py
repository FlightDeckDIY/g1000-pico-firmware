"""Text protocol adapter for G1P Flight Display Device.

This module converts the existing ASCII command protocol (used over
USB CDC today) into internal message objects, and can format response
messages back into human-readable lines that preserve current
behavior.

Messages are dicts of the form:
    {"type": MSG_*, "payload": {...}}

This adapter is meant to be used by handle_usb_command in main.py for
now, so that we can gradually transition from CDC text to HID binary
without changing higher-level logic.
"""

from protocol_ids import (
    # Message types
    MSG_DEVICE_INFO_REQUEST,
    MSG_RESET_REQUEST,
    MSG_SIM_STATUS_UPDATE,
    MSG_LED_MODE_SET,
    MSG_LED_BRIGHTNESS_SET,
    MSG_ELECTRICAL_MASTER_SET,
    MSG_ENCODER_STATS_RESPONSE,
    MSG_DEVICE_INFO_RESPONSE,
    # Enums
    SIM_STATUS_CONNECTED,
    SIM_STATUS_DISCONNECTED,
    LED_MODE_OFF,
    LED_MODE_ON,
    LED_MODE_FLASH,
    LED_MODE_BREATHE,
    LED_MODE_STEADY,
)


def decode_text_command(line):
    """Convert a single ASCII command line into a message dict.

    This mirrors the behavior of the previous handle_usb_command
    implementation but returns a high-level message instead of acting
    directly on application state.

    Returns:
        message dict or None if the command is unknown/ignored.
    """
    if not line:
        return None

    cmd = line.strip()

    # Exact matches first
    if cmd == "deviceInfo":
        return {"type": MSG_DEVICE_INFO_REQUEST, "payload": {}}

    if cmd == "reset":
        return {"type": MSG_RESET_REQUEST, "payload": {}}

    if cmd.lower() == "encoderstats":
        # Request stats; the router will turn this into a response
        # message that we can format below.
        from protocol_ids import MSG_ENCODER_STATS_REQUEST
        return {"type": MSG_ENCODER_STATS_REQUEST, "payload": {}}

    if cmd.lower() == "resetstats":
        from protocol_ids import MSG_ENCODER_STATS_RESET
        return {"type": MSG_ENCODER_STATS_RESET, "payload": {}}

    # simStatus:connected / simStatus:disconnected
    if cmd.startswith("simStatus:"):
        value = cmd[10:].strip().lower()
        status = SIM_STATUS_CONNECTED if value == "connected" else SIM_STATUS_DISCONNECTED
        return {
            "type": MSG_SIM_STATUS_UPDATE,
            "payload": {"status": status},
        }

    # LED commands: led:on/off/flash/breathe/steady or led:<0-100>
    if cmd.lower().startswith("led:"):
        value = cmd[4:].strip().lower()

        # Mode-based commands
        if value == "on":
            return {
                "type": MSG_LED_MODE_SET,
                "payload": {"mode": LED_MODE_ON},
            }
        if value == "off":
            return {
                "type": MSG_LED_MODE_SET,
                "payload": {"mode": LED_MODE_OFF},
            }
        if value == "flash":
            return {
                "type": MSG_LED_MODE_SET,
                "payload": {"mode": LED_MODE_FLASH},
            }
        if value == "breathe":
            return {
                "type": MSG_LED_MODE_SET,
                "payload": {"mode": LED_MODE_BREATHE},
            }
        if value == "steady":
            return {
                "type": MSG_LED_MODE_SET,
                "payload": {"mode": LED_MODE_STEADY},
            }

        # Numeric brightness
        try:
            brightness = int(value)
        except ValueError:
            # Invalid brightness string; ignore
            return None

        return {
            "type": MSG_LED_BRIGHTNESS_SET,
            "payload": {"brightness": brightness},
        }

    # electricalMaster:on/off
    if cmd.startswith("electricalMaster:"):
        value = cmd[17:].strip().lower()
        from protocol_ids import ELECTRICAL_MASTER_ON, ELECTRICAL_MASTER_OFF
        state = ELECTRICAL_MASTER_ON if value == "on" else ELECTRICAL_MASTER_OFF
        return {
            "type": MSG_ELECTRICAL_MASTER_SET,
            "payload": {"state": state},
        }

    # Unknown command – ignore silently (matches previous behavior)
    return None


def encode_text_responses(responses, mode_manager=None):
    """Convert response messages into printable text lines.

    This function is used to preserve the current CDC text behavior for
    commands like deviceInfo and encoderStats. It takes a list of
    response messages (as returned by CommandRouter.handle_message)
    and yields lines that should be printed.

    Args:
        responses: list of message dicts.
        mode_manager: optional, used to format current mode as PFD/MFD
            for some messages.

    Returns:
        A list of strings to print.
    """
    lines = []

    for resp in responses:
        msg_type = resp.get("type")
        payload = resp.get("payload") or {}

        if msg_type == MSG_DEVICE_INFO_RESPONSE:
            # Mirror existing deviceInfo output:
            #   DEVICE ID: <hex>
            #   Type: FDD G1P Rev 1 | Mode: PFD/MFD
            #   Firmware version: 0.1.1
            uid = payload.get("unique_id", "")
            fw_major = payload.get("fw_major", 0)
            fw_minor = payload.get("fw_minor", 0)
            fw_patch = payload.get("fw_patch", 0)

            # If mode_manager is provided, prefer that, otherwise use
            # numeric mode from payload.
            if mode_manager is not None:
                mode_str = "PFD" if getattr(mode_manager, "mode", 0) == 0 else "MFD"
            else:
                mode = payload.get("mode", 0)
                mode_str = "PFD" if mode == 0 else "MFD"

            lines.append("DEVICE ID: {}".format(uid))
            lines.append("Type: FDD G1P Rev 1 | Mode: {}".format(mode_str))
            lines.append("Firmware version: {}.{}.{}".format(fw_major, fw_minor, fw_patch))

        elif msg_type == MSG_ENCODER_STATS_RESPONSE:
            # Mirror existing encoderStats output:
            #   ENCODER_STATS:
            #     Buffer: <size>/<capacity>
            #     Overflows: <count>
            #     <encoder>: detents=X, invalid=Y, speed=Z
            buffer_size = payload.get("buffer_size", 0)
            buffer_capacity = payload.get("buffer_capacity", 0)
            buffer_overflows = payload.get("buffer_overflows", 0)
            encoders = payload.get("encoders", {})

            lines.append("ENCODER_STATS:")
            lines.append("  Buffer: {}/{}".format(buffer_size, buffer_capacity))
            lines.append("  Overflows: {}".format(buffer_overflows))

            for name, enc_stats in encoders.items():
                detents = enc_stats.get("total_detents", 0)
                invalid = enc_stats.get("invalid_transitions", 0)
                speed = enc_stats.get("last_speed", 0)
                lines.append(
                    "  {}: detents={}, invalid={}, speed={}".format(
                        name, detents, invalid, speed
                    )
                )

        # Other response types can be added here as needed.

    return lines
