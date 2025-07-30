from machine import Pin, unique_id
import time
import sys
import select
from binascii import hexlify


# Pin definitions with internal pull-ups
BUTTON_PIN = 28
ENCODER_DT_PIN = 16
ENCODER_CLK_PIN = 17
ENCODER_BTN_PIN = 26

# Command buffer
command_buffer = ""

class Button:
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self.last_state = True
        self.last_change = time.ticks_ms()
        self.debounce_time = 50  # milliseconds

    def is_pressed(self):
        current_time = time.ticks_ms()
        current_state = self.pin.value()
        
        if current_state != self.last_state and time.ticks_diff(current_time, self.last_change) > self.debounce_time:
            self.last_change = current_time
            self.last_state = current_state
            return not current_state  # Return True when button is pressed (pin goes low)
        return False

class RotaryEncoder:
    def __init__(self, dt_pin, clk_pin, btn_pin):
        self.dt = Pin(dt_pin, Pin.IN, Pin.PULL_UP)
        self.clk = Pin(clk_pin, Pin.IN, Pin.PULL_UP)
        self.btn = Pin(btn_pin, Pin.IN, Pin.PULL_UP)
        self.last_clk = self.clk.value()
        self.last_btn_state = True
        self.last_btn_change = time.ticks_ms()
        self.position = 0

    def read(self):
        # Returns: (rotation_change, button_pressed)
        rotation = 0
        current_clk = self.clk.value()
        
        if current_clk != self.last_clk:
            if self.dt.value() != current_clk:
                rotation = 1  # Clockwise
            else:
                rotation = -1  # Counter-clockwise
        
        self.last_clk = current_clk
        
        # Handle button press with debouncing
        current_time = time.ticks_ms()
        current_btn = self.btn.value()
        button_pressed = False
        
        if (current_btn != self.last_btn_state and 
            time.ticks_diff(current_time, self.last_btn_change) > 50):
            self.last_btn_change = current_time
            self.last_btn_state = current_btn
            if not current_btn:  # Button is pressed (goes low)
                button_pressed = True
        
        return rotation, button_pressed

def check_for_command():
    try:
        poller = select.poll()
        poller.register(sys.stdin, select.POLLIN)
        if poller.poll(0):  # Check if there's data available (0 timeout)
            line = sys.stdin.readline().strip()
            if line == "deviceId":
                id_hex = hexlify(unique_id()).decode('utf-8')
                print(f"DEVICE_ID:{id_hex}\n")
            elif line == "reset":
                print("RESETTING...\n")
                time.sleep(1)
                sys.exit()
            else:
                print("You typed: ", line)
    except (KeyboardInterrupt, AttributeError):
        print("Exiting...")
        sys.exit()

def main():
    # Initialize hardware
    button = Button(BUTTON_PIN)
    encoder = RotaryEncoder(ENCODER_DT_PIN, ENCODER_CLK_PIN, ENCODER_BTN_PIN)
    
    while True:
        # Check main button
        if button.is_pressed():
            print("BTN:PRESS\n")
            
        # Check encoder
        rotation, encoder_btn = encoder.read()
        if rotation != 0:
            print(f"ENC:{'+1' if rotation > 0 else '-1'}\n")
        if encoder_btn:
            print("ENC:BTN\n")
            
        # Check for serial commands
        check_for_command()
        
        time.sleep_ms(1)  # Small delay to prevent CPU overload

if __name__ == "__main__":
    main()
