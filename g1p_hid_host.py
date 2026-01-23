import time

import hid

from protocol_ids import (
    # Host -> device
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
    # Device -> host
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
    BUTTON_EVENT_PRESS,
    BUTTON_EVENT_RELEASE,
    BUTTON_EVENT_LONG_PRESS,
    PANEL_MODE_PFD,
    PANEL_MODE_MFD,
)

from protocol_binary import (
    REPORT_SIZE,
    encode_message_to_report,
    decode_report_to_message,
)


# ---------------------------------------------------------------------------
# Configuration: device identification
# ---------------------------------------------------------------------------

# Raspberry Pi / RP2 VID used by the custom UF2
VENDOR_ID = 0x2E8A
# Project-specific PID for the G1P HID interface
PRODUCT_ID = 0x10F7

# If you later expose multiple HID interfaces with the same VID/PID, you can
# optionally filter on usage_page/usage here.
PREFERRED_USAGE_PAGE = None  # e.g. 0xFF00 for vendor-specific
PREFERRED_USAGE = None       # e.g. 0x01 for a particular usage


# ---------------------------------------------------------------------------
# Device discovery and I/O helpers
# ---------------------------------------------------------------------------

def find_device():
    """Return an opened hid.Device for the G1P panel, or raise if not found."""
    candidates = []

    for info in hid.enumerate():
        if info["vendor_id"] != VENDOR_ID or info["product_id"] != PRODUCT_ID:
            continue

        if PREFERRED_USAGE_PAGE is not None and info.get("usage_page") not in (
            0,
            None,
            PREFERRED_USAGE_PAGE,
        ):
            continue

        if PREFERRED_USAGE is not None and info.get("usage") not in (0, None, PREFERRED_USAGE):
            continue

        candidates.append(info)

    if not candidates:
        raise RuntimeError("G1P HID device not found (check VID/PID and cabling).")

    info = candidates[0]
    dev = hid.Device(path=info["path"])
    dev.set_nonblocking(True)

    print("Opened HID device:")
    print(f"  Manufacturer: {info.get('manufacturer_string')}")
    print(f"  Product:      {info.get('product_string')}")
    print(f"  Serial:       {info.get('serial_number')}")
    print(f"  Usage page:   {info.get('usage_page')}, usage: {info.get('usage')}")

    return dev


def send_message(dev, msg):
    """Encode a message dict and send it as a single HID OUT report."""
    report = encode_message_to_report(msg)
    nwritten = dev.write(report)
    if nwritten != len(report):
        print(f"WARNING: wrote {nwritten} bytes, expected {len(report)}")


def read_one_message(dev):
    """Read a single HID report (non-blocking) and decode it.

    Returns:
        message dict, or None if no data / invalid / unknown message.
    """
    data = dev.read(REPORT_SIZE)
    if not data:
        return None

    msg = decode_report_to_message(bytes(data))
    return msg


# ---------------------------------------------------------------------------
# High-level host->device commands
# ---------------------------------------------------------------------------

def cmd_device_info(dev):
    send_message(dev, {"type": MSG_DEVICE_INFO_REQUEST, "payload": {}})


def cmd_reset(dev, reason_code=0):
    send_message(
        dev,
        {
            "type": MSG_RESET_REQUEST,
            "payload": {"reason_code": int(reason_code)},
        },
    )


def cmd_sim_status(dev, connected: bool):
    status = SIM_STATUS_CONNECTED if connected else SIM_STATUS_DISCONNECTED
    send_message(
        dev,
        {
            "type": MSG_SIM_STATUS_UPDATE,
            "payload": {"status": status},
        },
    )


def cmd_led_mode(dev, mode: int):
    """Mode is one of LED_MODE_* constants."""
    send_message(
        dev,
        {
            "type": MSG_LED_MODE_SET,
            "payload": {"mode": mode},
        },
    )


def cmd_led_brightness(dev, brightness: int):
    """Brightness 0–100."""
    send_message(
        dev,
        {
            "type": MSG_LED_BRIGHTNESS_SET,
            "payload": {"brightness": int(brightness)},
        },
    )


def cmd_electrical_master(dev, on: bool):
    state = ELECTRICAL_MASTER_ON if on else ELECTRICAL_MASTER_OFF
    send_message(
        dev,
        {
            "type": MSG_ELECTRICAL_MASTER_SET,
            "payload": {"state": state},
        },
    )


def cmd_encoder_stats_request(dev):
    send_message(
        dev,
        {
            "type": MSG_ENCODER_STATS_REQUEST,
            "payload": {},
        },
    )


def cmd_encoder_stats_reset(dev):
    send_message(
        dev,
        {
            "type": MSG_ENCODER_STATS_RESET,
            "payload": {},
        },
    )


# ---------------------------------------------------------------------------
# Pretty-printing incoming messages
# ---------------------------------------------------------------------------

def format_panel_mode(panel_mode_val):
    if panel_mode_val == PANEL_MODE_PFD:
        return "PFD"
    if panel_mode_val == PANEL_MODE_MFD:
        return "MFD"
    return f"UNKNOWN({panel_mode_val})"


def handle_incoming_message(msg):
    """Pretty-print a decoded message dict from the device."""
    if not msg:
        return

    msg_type = msg.get("type")
    payload = msg.get("payload") or {}

    if msg_type == MSG_DEVICE_INFO_RESPONSE:
        uid = payload.get("unique_id", "")
        fw = f"{payload.get('fw_major', 0)}.{payload.get('fw_minor', 0)}.{payload.get('fw_patch', 0)}"
        mode = format_panel_mode(payload.get("mode", 0))
        dev_type = payload.get("device_type", 0)
        print(f"[DEVICE_INFO] uid={uid} type={dev_type} mode={mode} fw={fw}")
        return

    if msg_type == MSG_ENCODER_STATS_RESPONSE:
        bs = payload.get("buffer_size", 0)
        bc = payload.get("buffer_capacity", 0)
        bo = payload.get("buffer_overflows", 0)
        print(f"[ENCODER_STATS] buffer={bs}/{bc} overflows={bo}")
        return

    if msg_type == MSG_ENCODER_EVENT:
        enc_id = payload.get("encoder_id")
        direction = payload.get("direction")
        speed = payload.get("speed")
        panel_mode = format_panel_mode(payload.get("panel_mode", 0))
        dir_str = "CW" if direction > 0 else "CCW" if direction < 0 else "NONE"
        print(f"[ENCODER_EVENT] id={enc_id} dir={dir_str} speed={speed} panel={panel_mode}")
        return

    if msg_type == MSG_BUTTON_EVENT:
        btn_id = payload.get("button_id")
        event_type = payload.get("event_type")
        panel_mode = format_panel_mode(payload.get("panel_mode", 0))
        if event_type == BUTTON_EVENT_PRESS:
            et = "PRESS"
        elif event_type == BUTTON_EVENT_RELEASE:
            et = "RELEASE"
        elif event_type == BUTTON_EVENT_LONG_PRESS:
            et = "LONG_PRESS"
        else:
            et = f"UNKNOWN({event_type})"
        print(f"[BUTTON_EVENT] id={btn_id} type={et} panel={panel_mode}")
        return

    if msg_type == MSG_HEARTBEAT_STATUS:
        seq = payload.get("sequence", 0)
        flags = payload.get("flags", 0)
        print(f"[HEARTBEAT_STATUS] seq={seq} flags=0x{flags:02X}")
        return

    if msg_type == MSG_ERROR_REPORT:
        severity = payload.get("severity", 0)
        code = payload.get("code", 0)
        detail0 = payload.get("detail0", 0)
        print(f"[ERROR] severity={severity} code=0x{code:02X} detail0=0x{detail0:02X}")
        return

    print("[MSG]", msg)


# ---------------------------------------------------------------------------
# Simple demo main
# ---------------------------------------------------------------------------

def main():
    dev = find_device()

    # Initial probe: ask for device info and encoder stats.
    cmd_device_info(dev)
    cmd_encoder_stats_request(dev)

    print("Listening for HID IN reports (Ctrl+C to quit)...")

    try:
        while True:
            msg = read_one_message(dev)
            if msg is not None:
                handle_incoming_message(msg)

            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        dev.close()


if __name__ == "__main__":
    main()
