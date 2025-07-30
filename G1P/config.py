from machine import Pin
from collections import namedtuple

# Pin definitions for main PCB
class Pins:
    # LED Backlight
    LED_BACKLIGHT = 21
    
    # Encoders with their respective pins
    # Format: (encoder_id, dt_pin, clk_pin)
    # Buttons should be defined separately in the BUTTONS list
    ENCODERS = [
        ("NAV_VOL", 5, 6),     # DT on 5, CLK on 6
        ("NAV_FRQ_MAJOR", 8, 10),  # DT on 8, CLK on 10
        ("NAV_FRQ_MINOR", 9, 11),  # DT on 9, CLK on 11
        ("HDG_BUG", 14, 15),   # DT on 14, CLK on 15
        ("ALT_MAJOR", 40, 41), # DT on 16, CLK on 17
        ("ALT_MINOR", 42, 43), # DT on 18, CLK on 19
    ]
    
    # Buttons (13x)
    # Format: (button_id, pin_number)
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

# USB Serial Configuration
class SerialConfig:
    BAUD_RATE = 115200
    MSG_PREFIX = "EVENT:"
    
    # Message formats
    class Messages:
        ROTARY = "{prefix}:ROTARY:{id}:{direction}:{speed}"
        BUTTON = "{prefix}:BUTTON:{id}:{action}"
        MODE_CHANGE = "{prefix}:MODE:{mode}"

# Mode switching configuration
class ModeConfig:
    MODE_SWITCH_BUTTON = "NAV_SWAP"  # Button to use for mode switching
    LONG_PRESS_MS = 3000          # Long press duration in milliseconds
    MODE_DEFAULT = 0 # Default mode (PFD)

# Encoder configuration
class EncoderConfig:
    # Acceleration settings
    ACCELERATION_ENABLED = True
    ACCEL_THRESHOLD = 3    # Number of steps before acceleration starts
    ACCEL_FACTOR = 2.0     # Multiplier for accelerated movement
    MAX_SPEED = 50         # Maximum speed value
    
    # Debounce time in milliseconds
    DEBOUNCE_MS = 20

# Button configuration
class ButtonConfig:
    # Debounce time in milliseconds
    DEBOUNCE_MS = 50
    
    # Button states
    PRESSED = 0
    RELEASED = 1
