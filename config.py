# Configuration constants for G1P Flight Display Device

# LED Configuration
LED_BACKLIGHT = 21
NAV_VOL_BRIGHTNESS_STEP = 5  # Percent per detent when adjusting backlight manually

# MCU Button Definitions
BUTTONS = [
    ("NAV_VOL_PUSH", 4),
    ("NAV_SWAP", 7),
    ("NAV_FQ_PUSH", 12),
    ("HDG_SYNC", 13),
    ("AP_TOGGLE", 16),
    ("AP_FD_TOGGLE", 17),
    ("AP_HDG_HOLD", 18),
    ("AP_ALT_HOLD", 19),
    ("AP_NAV_HOLD", 20),
    ("AP_VNV", 33),
    ("AP_APR", 35),
    ("AP_BC", 34),
    ("AP_VS_HOLD", 36),
    ("AP_NOSE_UP", 37),
    ("AP_FLC", 39),
    ("AP_NOSE_DOWN", 38),
    ("ALT_SYNC", 44)
]

# MCU Encoder Definitions
ENCODERS = [
    ("NAV_VOL", 5, 6, "single"),        # Pin A on GPIO5, Pin B on GPIO6 - Single detent
    ("NAV_FQ_MINOR", 8, 10, "dual"),   # Pin A on GPIO8, Pin B on GPIO10 - Dual detent
    ("NAV_FQ_MAJOR", 9, 11, "dual"),   # Pin A on GPIO9, Pin B on GPIO11 - Dual detent
    ("HDG_BUG", 14, 15, "single"),      # Pin A on GPIO14, Pin B on GPIO15 - Single detent
    ("ALT_MINOR", 40, 41, "dual"),      # Pin A on GPIO40, Pin B on GPIO41 - Dual detent
    ("ALT_MAJOR", 42, 43, "dual"),      # Pin A on GPIO42, Pin B on GPIO43 - Dual detent
]

# MCP23017 Pin Mappings
MCP23017_MAPS = {
    # Bottom PCB (Soft Keys) - 0x20
    "BOTTOM": {
        "port_a": [
            "NC",
            "NC",
            "SK7",
            "NC",
            "SK6",
            "SK5",
            "SK4",
            "SK3"
        ],
        "port_b": [
            "SK2",
            "SK1",
            "SK8",
            "SK9",
            "SK10",
            "SK11",
            "SK12",
            "NC"
        ]
    },
    # RIGHT PCB LOWER MCP23017 - 0x22
    "RIGHT_LOWER": {
        "port_a": [
            "CLR",
            "FPL",
            "DIRECT_TO",
            "CRS_BARO_CW_MINOR",
            "CRS_BARO_CCW_MINOR",
            "CRS_BARO_PUSH",
            "CRS_BARO_CW_MAJOR",
            "CRS_BARO_CCW_MAJOR"
        ],
        "port_b": [
            "MENU",
            "PROC",
            "ENT",
            "FMS_CW_MINOR",
            "FMS_CCW_MINOR",
            "FMS_CW_MAJOR",
            "FMS_PUSH",
            "FMS_CCW_MAJOR"
        ]
    },
    # RIGHT PCB UPPER MCP23017 - 0x24
    "RIGHT_UPPER": {
        "port_a": [
            "MAP_RIGHT",
            "MAP_CW",
            "COM_SWAP",
            "COM_FQ_CCW_MINOR",
            "COM_FQ_CW_MINOR",
            "COM_FQ_PUSH",
            "COM_FQ_CW_MAJOR",
            "COM_FQ_CCW_MAJOR",
        ],
        "port_b": [
            "COM_VOL_CW",
            "COM_VOL_CCW",
            "COM_VOL_PUSH",
            "MAP_UP",
            "MAP_PUSH",
            "MAP_LEFT",
            "MAP_CCW",
            "MAP_DOWN"
        ]
    }
}

# MCP23017 I2C Addresses
MCP23017_ADDRESSES = {
    "BOTTOM": 0x20,
    "RIGHT_LOWER": 0x22,
    "RIGHT_UPPER": 0x24,
}

# MCP23017 Encoder Detent Types
MCP_ENCODER_TYPES = {
    "COM_VOL_MINOR": "single",      # COM_VOL encoder - single detent
    "MAP_MINOR": "single",          # MAP encoder - single detent
    "CRS_BARO_MINOR": "dual",       # CRS_BARO encoder - dual detent
    "CRS_BARO_MAJOR": "dual",       # CRS_BARO encoder - dual detent
    "FMS_MINOR": "dual",            # FMS encoder - dual detent
    "FMS_MAJOR": "dual",            # FMS encoder - dual detent
    "COM_FQ_MINOR": "dual",         # COM_FQ encoder - dual detent
    "COM_FQ_MAJOR": "dual",         # COM_FQ encoder - dual detent
}

# MCP23017 Register Addresses
IODIRA   = 0x00
IODIRB   = 0x01
IPOLA    = 0x02
IPOLB    = 0x03
GPINTENA = 0x04
GPINTENB = 0x05
DEFVALA  = 0x06
DEFVALB  = 0x07
INTCONA  = 0x08
INTCONB  = 0x09
IOCON    = 0x0A  # same as 0x0B in BANK=0
GPPUA    = 0x0C
GPPUB    = 0x0D
INTFA    = 0x0E
INTFB    = 0x0F
INTCAPA  = 0x10
INTCAPB  = 0x11
GPIOA    = 0x12
GPIOB    = 0x13

# MCP23017 Configuration Values
BANK   = 0x80
MIRROR = 0x40  # Mirror INTA/INTB
SEQOP  = 0x20
DISSLW = 0x10
HAEN   = 0x08  # not used on MCP23017 (I2C)
ODR    = 0x04  # Open-drain INT output
INTPOL = 0x02  # Interrupt polarity (ignored if ODR=1)

# I2C Configuration
BUS_ID = 1
FREQ = 400000
SDA = 2
SCL = 3
INTERRUPT_PIN_NUMBER = 1

# USB Configuration
USB_BAUDRATE = 115200

# Timing Configuration (in milliseconds)
ENCODER_CHECK_INTERVAL = 1
MCP_CHECK_INTERVAL = 1
BUTTON_CHECK_INTERVAL = 20
USB_CHECK_INTERVAL = 5
LED_UPDATE_INTERVAL = 10

# Button Configuration
BUTTON_HOLD_THRESHOLD_MS = 2000  # 2 seconds in milliseconds
MAP_PUSH_TIMEOUT_MS = 15  # MAP button filtering timeout
MAP_DIRECTION_SUPPRESSION_WINDOW_MS = 50  # Direction button suppression window
MAP_BUTTON_REPEAT_INTERVAL_MS = 10  # Repeat interval for map direction buttons in milliseconds
MAP_REPEAT_DELAY_MS = 750  # ms before repeat starts
