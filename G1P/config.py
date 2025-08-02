from machine import Pin
from collections import namedtuple

class Mode:
    PFD = 0
    MFD = 1

    @staticmethod
    def name(mode_value):
        if mode_value == Mode.PFD:
            return "PFD"
        elif mode_value == Mode.MFD:
            return "MFD"
        else:
            return "UNKNOWN"

# For RP2350B, we use raw GPIO numbers (0-47)
# The machine.Pin class will handle these correctly if the firmware supports them

#-------------------------------------------------------------------------------------
# Pins
#-------------------------------------------------------------------------------------

# Pin definitions for main PCB
class Pins:
    # LED Backlight - Using raw GPIO number
    # For RP2350B, use the actual GPIO number (0-47)
    LED_BACKLIGHT = 21  # Update this to your actual LED GPIO
    
    # Encoders with their respective GPIO numbers for RP2350B
    # Format: (encoder_id, dt_gpio, clk_gpio)
    # Use raw GPIO numbers (0-47) for RP2350B
    ENCODERS = [
        ("NAV_VOL", 5, 6),      # DT on GPIO5, CLK on GPIO6
        ("NAV_FRQ_MAJOR", 8, 10),  # DT on GPIO8, CLK on GPIO10
        ("NAV_FRQ_MINOR", 9, 11),  # DT on GPIO9, CLK on GPIO11
        ("HDG_BUG", 14, 15),    # DT on GPIO14, CLK on GPIO15
        ("ALT_MAJOR", 40, 41),  # DT on GPIO40, CLK on GPIO41
        ("ALT_MINOR", 42, 43),  # DT on GPIO42, CLK on GPIO43
    ]
    
    # Note: For RP2350B, you need to ensure your MicroPython build supports these GPIOs
    # If you get 'invalid pin' errors, you may need to use a custom MicroPython build
    
    # Buttons with RP2350B GPIO numbers
    # Format: (button_id, gpio_number)
    # These are the raw GPIO numbers (0-47) for RP2350B
    BUTTONS = [
        ("NAV_VOL_PUSH", 4),    # GPIO4
        ("NAV_SWAP", 7),        # GPIO7
        ("NAV_FQ_PUSH", 12),    # GPIO12
        ("HDG_SYNC", 13),       # GPIO13
        ("AP_TOGGLE", 16),      # GPIO16
        ("AP_FD_TOGGLE", 17),   # GPIO17
        ("AP_HDG_HOLD", 18),    # GPIO18
        ("AP_ALT_HOLD", 19),    # GPIO19
        ("AP_NAV_HOLD", 20),    # GPIO20
        ("AP_VNV", 33),         # GPIO33
        ("AP_APR", 35),         # GPIO35
        ("AP_BC", 34),          # GPIO34
        ("AP_VS_HOLD", 36),     # GPIO36
        ("AP_NOSE_UP", 37),     # GPIO37
        ("AP_FLC", 39),         # GPIO39
        ("AP_NOSE_DOWN", 38),   # GPIO38
        ("ALT_SYNC", 44)        # GPIO44
    ]
    
    # Important: Ensure your MicroPython build supports these GPIOs
    # If you get 'invalid pin' errors, you may need to:
    # 1. Use a custom MicroPython build that supports RP2350B
    # 2. Or map these to the available GPIOs in your current firmware

#-------------------------------------------------------------------------------------
# USB Serial Configuration
#-------------------------------------------------------------------------------------

class SerialConfig:
    BAUD_RATE = 115200
    MSG_PREFIX = "EVENT:"
    
    # Message formats
    class Messages:
        ROTARY = "{prefix}:ROTARY:{id}:{direction}:{speed}"
        BUTTON = "{prefix}:BUTTON:{id}:{action}"
        MODE_CHANGE = "{prefix}:MODE:{mode}"

#-------------------------------------------------------------------------------------
# Mode Configuration
#-------------------------------------------------------------------------------------

class ModeConfig:
    MODE_SWITCH_BUTTON = "NAV_SWAP"  # Button to use for mode switching
    LONG_PRESS_MS = 3000             # Long press duration in milliseconds
    MODE_DEFAULT = Mode.PFD          # Default mode (PFD)

#-------------------------------------------------------------------------------------
# Encoder Configuration
#-------------------------------------------------------------------------------------

class EncoderConfig:
    # Acceleration settings
    ACCELERATION_ENABLED = True
    ACCEL_THRESHOLD = 3    # Number of steps before acceleration starts
    ACCEL_FACTOR = 2.0     # Multiplier for accelerated movement
    MAX_SPEED = 50         # Maximum speed value
    
    # Debounce time in milliseconds
    DEBOUNCE_MS = 20

#-------------------------------------------------------------------------------------
# Button Configuration
#-------------------------------------------------------------------------------------

class ButtonConfig:
    # Debounce time in milliseconds
    DEBOUNCE_MS = 50
    
    # Button states
    PRESSED = 0
    RELEASED = 1
