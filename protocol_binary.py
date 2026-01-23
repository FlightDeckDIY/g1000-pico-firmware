"""Binary protocol adapter for G1P Flight Display Device.

This module converts between internal message dicts
    {"type": MSG_*, "payload": {...}}

and fixed-size HID report payloads (64 bytes). It is transport-agnostic
beyond the report layout and does not talk to USB directly.

Report layout:
    Byte 0: report_id (1 = host->device, 2 = device->host by default)
    Byte 1: msg_type (MSG_*)
    Byte 2: length (number of payload bytes used)
    Byte 3..(3+length-1): payload bytes
    Remaining bytes are zero-padded.

This focuses on correctness and clarity over micro-optimizations.
"""

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
    MSG_HEARTBEAT,
    MSG_MODE_SET,
    MSG_DEVICE_INFO_RESPONSE,
    MSG_ENCODER_EVENT,
    MSG_BUTTON_EVENT,
    MSG_ENCODER_STATS_RESPONSE,
    MSG_HEARTBEAT_STATUS,
    MSG_ERROR_REPORT,
    # Enums
    SIM_STATUS_CONNECTED,
    SIM_STATUS_DISCONNECTED,
    LED_MODE_OFF,
    LED_MODE_ON,
    LED_MODE_FLASH,
    LED_MODE_BREATHE,
    LED_MODE_STEADY,
    ELECTRICAL_MASTER_OFF,
    ELECTRICAL_MASTER_ON,
    PANEL_MODE_PFD,
    PANEL_MODE_MFD,
    BUTTON_EVENT_PRESS,
    BUTTON_EVENT_RELEASE,
    BUTTON_EVENT_LONG_PRESS,
    ERROR_SEVERITY_INFO,
    ERROR_SEVERITY_WARNING,
    ERROR_SEVERITY_ERROR,
)


REPORT_SIZE = 64
REPORT_ID_HOST_TO_DEVICE = 0x01
REPORT_ID_DEVICE_TO_HOST = 0x02


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def encode_message_to_report(message, report_id=REPORT_ID_HOST_TO_DEVICE):
    """Encode a message dict into a 64-byte HID report.

    Args:
        message: {"type": MSG_*, "payload": {...}}
        report_id: which report ID to use (1 or 2 typically).

    Returns:
        bytes of length REPORT_SIZE.
    """
    msg_type = message.get("type")
    payload = message.get("payload") or {}

    buf = bytearray(REPORT_SIZE)
    buf[0] = report_id & 0xFF
    buf[1] = msg_type & 0xFF

    # We fill buf[2] (length) once we know how many payload bytes we wrote.
    length = 0

    # Host -> device commands ------------------------------------------------
    if msg_type == MSG_DEVICE_INFO_REQUEST:
        # No payload
        length = 0

    elif msg_type == MSG_RESET_REQUEST:
        # Byte 3: reason_code (optional, default 0)
        reason = int(payload.get("reason_code", 0)) & 0xFF
        buf[3] = reason
        length = 1

    elif msg_type == MSG_SIM_STATUS_UPDATE:
        status = payload.get("status", SIM_STATUS_CONNECTED)
        buf[3] = SIM_STATUS_CONNECTED if status == SIM_STATUS_CONNECTED else SIM_STATUS_DISCONNECTED
        length = 1

    elif msg_type == MSG_LED_MODE_SET:
        mode = payload.get("mode", LED_MODE_ON)
        buf[3] = int(mode) & 0xFF
        length = 1

    elif msg_type == MSG_LED_BRIGHTNESS_SET:
        brightness = int(payload.get("brightness", 0)) & 0xFF
        buf[3] = brightness
        length = 1

    elif msg_type == MSG_ELECTRICAL_MASTER_SET:
        state = payload.get("state", ELECTRICAL_MASTER_OFF)
        buf[3] = ELECTRICAL_MASTER_ON if state == ELECTRICAL_MASTER_ON else ELECTRICAL_MASTER_OFF
        length = 1

    elif msg_type == MSG_ENCODER_STATS_REQUEST:
        length = 0

    elif msg_type == MSG_ENCODER_STATS_RESET:
        length = 0

    elif msg_type == MSG_HEARTBEAT:
        seq = int(payload.get("sequence", 0)) & 0xFF
        buf[3] = seq
        length = 1

    elif msg_type == MSG_MODE_SET:
        mode = int(payload.get("mode", 0)) & 0xFF
        buf[3] = mode
        length = 1

    # Device -> host responses/events ---------------------------------------
    elif msg_type == MSG_DEVICE_INFO_RESPONSE:
        # Payload fields we expect:
        #  protocol_version: uint8
        #  device_type:      uint8
        #  mode:             uint8
        #  fw_major/minor/patch: uint8
        #  unique_id: string (we encode as ASCII, truncated/padded to 16 bytes)
        proto_ver = int(payload.get("protocol_version", 1)) & 0xFF
        dev_type = int(payload.get("device_type", 0)) & 0xFF
        mode = int(payload.get("mode", 0)) & 0xFF
        fw_major = int(payload.get("fw_major", 0)) & 0xFF
        fw_minor = int(payload.get("fw_minor", 0)) & 0xFF
        fw_patch = int(payload.get("fw_patch", 0)) & 0xFF
        uid_str = str(payload.get("unique_id", ""))
        uid_bytes = uid_str.encode("ascii", "ignore")[:16]

        idx = 3
        buf[idx] = proto_ver; idx += 1
        buf[idx] = dev_type; idx += 1
        buf[idx] = mode; idx += 1
        buf[idx] = fw_major; idx += 1
        buf[idx] = fw_minor; idx += 1
        buf[idx] = fw_patch; idx += 1

        # Unique ID (16 bytes, padded with 0)
        for i in range(16):
            buf[idx + i] = uid_bytes[i] if i < len(uid_bytes) else 0
        idx += 16

        length = idx - 3

    elif msg_type == MSG_ENCODER_STATS_RESPONSE:
        # Expect:
        #  buffer_size:      uint16
        #  buffer_capacity:  uint16
        #  buffer_overflows: uint16
        buf_size = int(payload.get("buffer_size", 0)) & 0xFFFF
        buf_cap = int(payload.get("buffer_capacity", 0)) & 0xFFFF
        buf_ovf = int(payload.get("buffer_overflows", 0)) & 0xFFFF

        idx = 3
        # buffer_size
        buf[idx] = buf_size & 0xFF; buf[idx+1] = (buf_size >> 8) & 0xFF; idx += 2
        # buffer_capacity
        buf[idx] = buf_cap & 0xFF; buf[idx+1] = (buf_cap >> 8) & 0xFF; idx += 2
        # buffer_overflows
        buf[idx] = buf_ovf & 0xFF; buf[idx+1] = (buf_ovf >> 8) & 0xFF; idx += 2

        length = idx - 3

    elif msg_type == MSG_ENCODER_EVENT:
        # Payload:
        #  encoder_id: uint8
        #  direction:  int8  (-1, 0, +1 encoded as 0xFF, 0x00, 0x01)
        #  speed:      uint8
        #  panel_mode: uint8 (PANEL_MODE_PFD / PANEL_MODE_MFD)
        encoder_id = int(payload.get("encoder_id", 0)) & 0xFF
        direction = int(payload.get("direction", 0))
        if direction < 0:
            direction_byte = 0xFF
        elif direction > 0:
            direction_byte = 0x01
        else:
            direction_byte = 0x00
        speed = int(payload.get("speed", 1)) & 0xFF
        panel_mode = int(payload.get("panel_mode", PANEL_MODE_PFD)) & 0xFF

        idx = 3
        buf[idx] = encoder_id; idx += 1
        buf[idx] = direction_byte; idx += 1
        buf[idx] = speed; idx += 1
        buf[idx] = panel_mode; idx += 1

        length = idx - 3

    elif msg_type == MSG_BUTTON_EVENT:
        # Payload:
        #  button_id:  uint8
        #  event_type: uint8 (BUTTON_EVENT_*)
        #  panel_mode:uint8
        button_id = int(payload.get("button_id", 0)) & 0xFF
        event_type = int(payload.get("event_type", BUTTON_EVENT_PRESS)) & 0xFF
        panel_mode = int(payload.get("panel_mode", PANEL_MODE_PFD)) & 0xFF

        idx = 3
        buf[idx] = button_id; idx += 1
        buf[idx] = event_type; idx += 1
        buf[idx] = panel_mode; idx += 1

        length = idx - 3

    elif msg_type == MSG_HEARTBEAT_STATUS:
        # Simple echo of last sequence and optional flags
        seq = int(payload.get("sequence", 0)) & 0xFF
        flags = int(payload.get("flags", 0)) & 0xFF
        idx = 3
        buf[idx] = seq; idx += 1
        buf[idx] = flags; idx += 1
        length = idx - 3

    elif msg_type == MSG_ERROR_REPORT:
        # Minimal error report:
        #  severity: uint8
        #  code:     uint8
        #  detail0:  uint8 (optional extra info)
        severity = int(payload.get("severity", ERROR_SEVERITY_INFO)) & 0xFF
        code = int(payload.get("code", 0)) & 0xFF
        detail0 = int(payload.get("detail0", 0)) & 0xFF
        idx = 3
        buf[idx] = severity; idx += 1
        buf[idx] = code; idx += 1
        buf[idx] = detail0; idx += 1
        length = idx - 3

    else:
        # Unknown message type – leave payload empty. Caller can decide
        # whether to send or drop.
        length = 0

    buf[2] = length & 0xFF
    return bytes(buf)


# ---------------------------------------------------------------------------
# Decoding helpers
# ---------------------------------------------------------------------------

def decode_report_to_message(report_bytes):
    """Decode a 64-byte HID report into a single message dict.

    Args:
        report_bytes: bytes or bytearray of length REPORT_SIZE.

    Returns:
        message dict {"type": MSG_*, "payload": {...}} or None if
        the report is invalid/unsupported.
    """
    if not report_bytes or len(report_bytes) < 3:
        return None

    b = report_bytes
    report_id = b[0]
    msg_type = b[1]
    length = b[2]

    # Clamp length to available bytes after header
    max_len = len(b) - 3
    if length > max_len:
        length = max_len

    payload = {}
    idx = 3

    # Host -> device ---------------------------------------------------------
    if msg_type == MSG_DEVICE_INFO_REQUEST:
        # No payload
        pass

    elif msg_type == MSG_RESET_REQUEST:
        reason = b[idx] if length >= 1 else 0
        payload["reason_code"] = reason

    elif msg_type == MSG_SIM_STATUS_UPDATE:
        status = b[idx] if length >= 1 else SIM_STATUS_DISCONNECTED
        if status != SIM_STATUS_CONNECTED:
            status = SIM_STATUS_DISCONNECTED
        payload["status"] = status

    elif msg_type == MSG_LED_MODE_SET:
        mode = b[idx] if length >= 1 else LED_MODE_ON
        if mode not in (LED_MODE_OFF, LED_MODE_ON, LED_MODE_FLASH,
                        LED_MODE_BREATHE, LED_MODE_STEADY):
            mode = LED_MODE_ON
        payload["mode"] = mode

    elif msg_type == MSG_LED_BRIGHTNESS_SET:
        brightness = b[idx] if length >= 1 else 0
        payload["brightness"] = brightness

    elif msg_type == MSG_ELECTRICAL_MASTER_SET:
        state = b[idx] if length >= 1 else ELECTRICAL_MASTER_OFF
        if state != ELECTRICAL_MASTER_ON:
            state = ELECTRICAL_MASTER_OFF
        payload["state"] = state

    elif msg_type == MSG_ENCODER_STATS_REQUEST:
        pass

    elif msg_type == MSG_ENCODER_STATS_RESET:
        pass

    elif msg_type == MSG_HEARTBEAT:
        seq = b[idx] if length >= 1 else 0
        payload["sequence"] = seq

    elif msg_type == MSG_MODE_SET:
        mode = b[idx] if length >= 1 else 0
        payload["mode"] = mode

    # Device -> host ---------------------------------------------------------
    elif msg_type == MSG_DEVICE_INFO_RESPONSE:
        # Decode fields in the same order as encode.
        if length >= 6:
            proto_ver = b[idx]; dev_type = b[idx+1]; mode = b[idx+2]
            fw_major = b[idx+3]; fw_minor = b[idx+4]; fw_patch = b[idx+5]
            idx_local = idx + 6
            uid_bytes = b[idx_local:idx_local+16]
            try:
                uid_str = bytes(uid_bytes).decode("ascii", "ignore").rstrip("\x00")
            except Exception:
                uid_str = ""
            payload.update({
                "protocol_version": proto_ver,
                "device_type": dev_type,
                "mode": mode,
                "fw_major": fw_major,
                "fw_minor": fw_minor,
                "fw_patch": fw_patch,
                "unique_id": uid_str,
            })

    elif msg_type == MSG_ENCODER_STATS_RESPONSE:
        # buffer_size, buffer_capacity, buffer_overflows as uint16 each
        if length >= 6:
            bs = b[idx] | (b[idx+1] << 8)
            bc = b[idx+2] | (b[idx+3] << 8)
            bo = b[idx+4] | (b[idx+5] << 8)
            payload.update({
                "buffer_size": bs,
                "buffer_capacity": bc,
                "buffer_overflows": bo,
                # Per-encoder stats are not encoded here; they can be
                # requested via a richer mechanism if needed.
                "encoders": {},
            })

    elif msg_type == MSG_ENCODER_EVENT:
        # encoder_id, direction, speed, panel_mode
        if length >= 4:
            encoder_id = b[idx]; direction_byte = b[idx+1]; speed = b[idx+2]; panel_mode = b[idx+3]
            if direction_byte == 0xFF:
                direction = -1
            elif direction_byte == 0x01:
                direction = 1
            else:
                direction = 0
            payload.update({
                "encoder_id": encoder_id,
                "direction": direction,
                "speed": speed,
                "panel_mode": panel_mode,
            })

    elif msg_type == MSG_BUTTON_EVENT:
        if length >= 3:
            button_id = b[idx]; event_type = b[idx+1]; panel_mode = b[idx+2]
            payload.update({
                "button_id": button_id,
                "event_type": event_type,
                "panel_mode": panel_mode,
            })

    elif msg_type == MSG_HEARTBEAT_STATUS:
        if length >= 2:
            seq = b[idx]; flags = b[idx+1]
            payload.update({
                "sequence": seq,
                "flags": flags,
            })

    elif msg_type == MSG_ERROR_REPORT:
        if length >= 3:
            severity = b[idx]; code = b[idx+1]; detail0 = b[idx+2]
            payload.update({
                "severity": severity,
                "code": code,
                "detail0": detail0,
            })

    else:
        # Unknown message type – ignore.
        return None

    return {"type": msg_type, "payload": payload}
