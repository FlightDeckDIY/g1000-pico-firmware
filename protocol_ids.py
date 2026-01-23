"""Protocol and ID definitions for G1P Flight Display Device.

This module centralizes numeric IDs used by the USB/HID protocol and
internal command layer so that firmware and host code can share a
consistent view of message types, encoders, buttons, and error codes.

NOTE: This is transport-agnostic. It does not deal with bytes or HID
reports directly; it just defines constants you can mirror on the host.
"""

# Message types (host -> device)
MSG_DEVICE_INFO_REQUEST      = 0x01
MSG_RESET_REQUEST            = 0x02
MSG_SIM_STATUS_UPDATE        = 0x03
MSG_LED_MODE_SET             = 0x04
MSG_LED_BRIGHTNESS_SET       = 0x05
MSG_ELECTRICAL_MASTER_SET    = 0x06
MSG_ENCODER_STATS_REQUEST    = 0x07
MSG_ENCODER_STATS_RESET      = 0x08
MSG_HEARTBEAT                = 0x09
MSG_MODE_SET                 = 0x0A  # optional / future

# Message types (device -> host)
MSG_DEVICE_INFO_RESPONSE     = 0x81
MSG_ENCODER_EVENT            = 0x82
MSG_BUTTON_EVENT             = 0x83
MSG_ENCODER_STATS_RESPONSE   = 0x84
MSG_HEARTBEAT_STATUS         = 0x85
MSG_ERROR_REPORT             = 0x86

# Panel modes
PANEL_MODE_PFD = 0x00
PANEL_MODE_MFD = 0x01

# Sim status
SIM_STATUS_DISCONNECTED = 0x00
SIM_STATUS_CONNECTED    = 0x01

# LED modes
LED_MODE_OFF     = 0x00
LED_MODE_ON      = 0x01
LED_MODE_FLASH   = 0x02
LED_MODE_BREATHE = 0x03
LED_MODE_STEADY  = 0x04

# Electrical master state
ELECTRICAL_MASTER_OFF = 0x00
ELECTRICAL_MASTER_ON  = 0x01

# Button event types
BUTTON_EVENT_PRESS      = 0x00
BUTTON_EVENT_RELEASE    = 0x01
BUTTON_EVENT_LONG_PRESS = 0x02

# Error severity
ERROR_SEVERITY_INFO    = 0x00
ERROR_SEVERITY_WARNING = 0x01
ERROR_SEVERITY_ERROR   = 0x02

# Device types
DEVICE_TYPE_FDD_G1P_REV1 = 0x01

# Encoder IDs (direct MCU encoders from config.ENCODERS)
ENCODER_ID_NAV_VOL      = 0x01
ENCODER_ID_NAV_FQ_MINOR = 0x02
ENCODER_ID_NAV_FQ_MAJOR = 0x03
ENCODER_ID_HDG_BUG      = 0x04
ENCODER_ID_ALT_MINOR    = 0x05
ENCODER_ID_ALT_MAJOR    = 0x06

# Encoder IDs (MCP23017 / panel encoders)
ENCODER_ID_CRS_BARO_MINOR = 0x10
ENCODER_ID_CRS_BARO_MAJOR = 0x11
ENCODER_ID_FMS_MINOR      = 0x12
ENCODER_ID_FMS_MAJOR      = 0x13
ENCODER_ID_COM_FQ_MINOR   = 0x14
ENCODER_ID_COM_FQ_MAJOR   = 0x15
ENCODER_ID_COM_VOL        = 0x16
ENCODER_ID_MAP            = 0x17

# Mapping from logical encoder names to IDs
ENCODER_IDS = {
    # Direct encoders
    "NAV_VOL":       ENCODER_ID_NAV_VOL,
    "NAV_FQ_MINOR":  ENCODER_ID_NAV_FQ_MINOR,
    "NAV_FQ_MAJOR":  ENCODER_ID_NAV_FQ_MAJOR,
    "HDG_BUG":       ENCODER_ID_HDG_BUG,
    "ALT_MINOR":     ENCODER_ID_ALT_MINOR,
    "ALT_MAJOR":     ENCODER_ID_ALT_MAJOR,

    # MCP encoders – names as produced by MCP23017Handler.encoder_pairs
    "CRS_BARO_MINOR": ENCODER_ID_CRS_BARO_MINOR,
    "CRS_BARO_MAJOR": ENCODER_ID_CRS_BARO_MAJOR,
    "FMS_MINOR":      ENCODER_ID_FMS_MINOR,
    "FMS_MAJOR":      ENCODER_ID_FMS_MAJOR,
    "COM_FQ_MINOR":   ENCODER_ID_COM_FQ_MINOR,
    "COM_FQ_MAJOR":   ENCODER_ID_COM_FQ_MAJOR,
    "COM_VOL":        ENCODER_ID_COM_VOL,
    "MAP":            ENCODER_ID_MAP,
}

# Button IDs (direct MCU buttons from config.BUTTONS)
BUTTON_ID_NAV_VOL_PUSH  = 0x01
BUTTON_ID_NAV_SWAP      = 0x02
BUTTON_ID_NAV_FQ_PUSH   = 0x03
BUTTON_ID_HDG_SYNC      = 0x04
BUTTON_ID_AP_TOGGLE     = 0x05
BUTTON_ID_AP_FD_TOGGLE  = 0x06
BUTTON_ID_AP_HDG_HOLD   = 0x07
BUTTON_ID_AP_ALT_HOLD   = 0x08
BUTTON_ID_AP_NAV_HOLD   = 0x09
BUTTON_ID_AP_VNV        = 0x0A
BUTTON_ID_AP_APR        = 0x0B
BUTTON_ID_AP_BC         = 0x0C
BUTTON_ID_AP_VS_HOLD    = 0x0D
BUTTON_ID_AP_NOSE_UP    = 0x0E
BUTTON_ID_AP_FLC        = 0x0F
BUTTON_ID_AP_NOSE_DOWN  = 0x10
BUTTON_ID_ALT_SYNC      = 0x11

# Button IDs – softkeys (SK1–SK12 on BOTTOM MCP)
BUTTON_ID_SK1  = 0x40
BUTTON_ID_SK2  = 0x41
BUTTON_ID_SK3  = 0x42
BUTTON_ID_SK4  = 0x43
BUTTON_ID_SK5  = 0x44
BUTTON_ID_SK6  = 0x45
BUTTON_ID_SK7  = 0x46
BUTTON_ID_SK8  = 0x47
BUTTON_ID_SK9  = 0x48
BUTTON_ID_SK10 = 0x49
BUTTON_ID_SK11 = 0x4A
BUTTON_ID_SK12 = 0x4B

# Button IDs – RIGHT_LOWER function buttons
BUTTON_ID_CLR          = 0x50
BUTTON_ID_FPL          = 0x51
BUTTON_ID_DIRECT_TO    = 0x52
BUTTON_ID_CRS_BARO_PUSH= 0x53
BUTTON_ID_MENU         = 0x54
BUTTON_ID_PROC         = 0x55
BUTTON_ID_ENT          = 0x56
BUTTON_ID_FMS_PUSH     = 0x57

# Button IDs – RIGHT_UPPER COM/MAP
BUTTON_ID_COM_SWAP     = 0x60
BUTTON_ID_COM_FQ_PUSH  = 0x61
BUTTON_ID_COM_VOL_PUSH = 0x62
BUTTON_ID_MAP_PUSH     = 0x63
BUTTON_ID_MAP_UP       = 0x64
BUTTON_ID_MAP_DOWN     = 0x65
BUTTON_ID_MAP_LEFT     = 0x66
BUTTON_ID_MAP_RIGHT    = 0x67

# Mapping from logical button names (as used in ButtonHandler/button_states)
# to numeric button IDs. This lets the firmware emit stable IDs while
# keeping all existing naming in config.py and handlers.
BUTTON_IDS = {
    # Direct MCU buttons
    "NAV_VOL_PUSH":  BUTTON_ID_NAV_VOL_PUSH,
    "NAV_SWAP":      BUTTON_ID_NAV_SWAP,
    "NAV_FQ_PUSH":   BUTTON_ID_NAV_FQ_PUSH,
    "HDG_SYNC":      BUTTON_ID_HDG_SYNC,
    "AP_TOGGLE":     BUTTON_ID_AP_TOGGLE,
    "AP_FD_TOGGLE":  BUTTON_ID_AP_FD_TOGGLE,
    "AP_HDG_HOLD":   BUTTON_ID_AP_HDG_HOLD,
    "AP_ALT_HOLD":   BUTTON_ID_AP_ALT_HOLD,
    "AP_NAV_HOLD":   BUTTON_ID_AP_NAV_HOLD,
    "AP_VNV":        BUTTON_ID_AP_VNV,
    "AP_APR":        BUTTON_ID_AP_APR,
    "AP_BC":         BUTTON_ID_AP_BC,
    "AP_VS_HOLD":    BUTTON_ID_AP_VS_HOLD,
    "AP_NOSE_UP":    BUTTON_ID_AP_NOSE_UP,
    "AP_FLC":        BUTTON_ID_AP_FLC,
    "AP_NOSE_DOWN":  BUTTON_ID_AP_NOSE_DOWN,
    "ALT_SYNC":      BUTTON_ID_ALT_SYNC,

    # Softkeys
    "SK1":           BUTTON_ID_SK1,
    "SK2":           BUTTON_ID_SK2,
    "SK3":           BUTTON_ID_SK3,
    "SK4":           BUTTON_ID_SK4,
    "SK5":           BUTTON_ID_SK5,
    "SK6":           BUTTON_ID_SK6,
    "SK7":           BUTTON_ID_SK7,
    "SK8":           BUTTON_ID_SK8,
    "SK9":           BUTTON_ID_SK9,
    "SK10":          BUTTON_ID_SK10,
    "SK11":          BUTTON_ID_SK11,
    "SK12":          BUTTON_ID_SK12,

    # RIGHT_LOWER buttons
    "CLR":           BUTTON_ID_CLR,
    "FPL":           BUTTON_ID_FPL,
    "DIRECT_TO":     BUTTON_ID_DIRECT_TO,
    "CRS_BARO_PUSH": BUTTON_ID_CRS_BARO_PUSH,
    "MENU":          BUTTON_ID_MENU,
    "PROC":          BUTTON_ID_PROC,
    "ENT":           BUTTON_ID_ENT,
    "FMS_PUSH":      BUTTON_ID_FMS_PUSH,

    # RIGHT_UPPER buttons
    "COM_SWAP":      BUTTON_ID_COM_SWAP,
    "COM_FQ_PUSH":   BUTTON_ID_COM_FQ_PUSH,
    "COM_VOL_PUSH":  BUTTON_ID_COM_VOL_PUSH,
    "MAP_PUSH":      BUTTON_ID_MAP_PUSH,
    "MAP_UP":        BUTTON_ID_MAP_UP,
    "MAP_DOWN":      BUTTON_ID_MAP_DOWN,
    "MAP_LEFT":      BUTTON_ID_MAP_LEFT,
    "MAP_RIGHT":     BUTTON_ID_MAP_RIGHT,
}

# Error codes
ERROR_PROTOCOL_DECODE_ERROR        = 0x01
ERROR_CMD_UNSUPPORTED              = 0x02
ERROR_CMD_HANDLER_EXCEPTION        = 0x03

ERROR_USB_GENERIC_ERROR            = 0x10
ERROR_USB_READ_ERROR               = 0x11
ERROR_USB_HANDLER_ERROR            = 0x12

ERROR_LED_ERROR                    = 0x20
ERROR_ELECTRICAL_MASTER_ERROR      = 0x21

ERROR_MCP_NO_DEVICES_FOUND         = 0x30
ERROR_MCP_INIT_FAILED              = 0x31
ERROR_MCP_READ_REGISTER_ERROR      = 0x32
ERROR_MCP_DEVICE_READ_ERROR        = 0x33

ERROR_ENCODER_INVALID_TRANSITION   = 0x40
ERROR_ENCODER_BUFFER_OVERFLOW      = 0x41
ERROR_ENCODER_HANDLER_NOT_INIT     = 0x42
