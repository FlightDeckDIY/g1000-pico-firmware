from machine import Pin, I2C, Timer
import time
import micropython
from config import (
    Pins, ButtonConfig, EncoderConfig, 
    ModeConfig, SerialConfig
)

# Allocate memory for interrupt handlers
micropython.alloc_emergency_exception_buf(100)

class Button:
    """Debounced button with press/release detection."""
    def __init__(self, button_id, pin_num):
        self.id = button_id
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self.last_state = ButtonConfig.RELEASED
        self.last_change = time.ticks_ms()
        self.press_callback = None
        self.release_callback = None
        self.long_press_callback = None
        self.long_press_start = None
        self.long_press_triggered = False

    def update(self):
        """Update button state and trigger callbacks."""
        current_time = time.ticks_ms()
        current_state = self.pin.value()
        
        # State change detection with debouncing
        if (current_state != self.last_state and 
            time.ticks_diff(current_time, self.last_change) > ButtonConfig.DEBOUNCE_MS):
            
            self.last_change = current_time
            
            if current_state == ButtonConfig.PRESSED:
                # Button was just pressed
                self.long_press_triggered = False
                self.long_press_start = current_time
                if self.press_callback:
                    self.press_callback(self.id)
            else:
                # Button was just released
                if not self.long_press_triggered and self.release_callback:
                    self.release_callback(self.id)
                self.long_press_start = None
                self.long_press_triggered = False
            
            self.last_state = current_state
        
        # Check for long press
        if (self.long_press_start is not None and 
            not self.long_press_triggered and
            time.ticks_diff(current_time, self.long_press_start) > ModeConfig.LONG_PRESS_MS and
            self.long_press_callback):
            
            self.long_press_triggered = True
            self.long_press_callback(self.id)

class RotaryEncoder:
    """Rotary encoder with acceleration support."""
    def __init__(self, encoder_id, dt_pin, clk_pin):
        self.id = encoder_id
        self.dt = Pin(dt_pin, Pin.IN, Pin.PULL_UP)
        self.clk = Pin(clk_pin, Pin.IN, Pin.PULL_UP)
        
        self.last_clk = self.clk.value()
        self.position = 0
        self.last_step_time = time.ticks_ms()
        self.step_count = 0
        
        # Initialize callbacks
        self.rotation_callback = None

    def update(self):
        """Update encoder state and trigger callbacks."""
        current_clk = self.clk.value()
        if current_clk != self.last_clk:
            now = time.ticks_ms()
            dt = time.ticks_diff(now, self.last_step_time)
            self.last_step_time = now
            
            # Determine direction
            if self.dt.value() != current_clk:
                direction = 1  # Clockwise
            else:
                direction = -1  # Counter-clockwise
            
            # Calculate speed/acceleration
            speed = 1
            if EncoderConfig.ACCELERATION_ENABLED:
                if dt < 100:  # Only accelerate for quick successive turns
                    self.step_count = min(self.step_count + 1, EncoderConfig.ACCEL_THRESHOLD * 2)
                    if self.step_count > EncoderConfig.ACCEL_THRESHOLD:
                        speed = min(
                            EncoderConfig.ACCEL_FACTOR * 
                            (self.step_count - EncoderConfig.ACCEL_THRESHOLD + 1),
                            EncoderConfig.MAX_SPEED
                        )
                else:
                    self.step_count = 0
            
            # Update position and trigger callback
            self.position += direction * speed
            if self.rotation_callback:
                self.rotation_callback(self.id, direction, speed)
            
            self.last_clk = current_clk
        
        # Reset step count if no movement for a while
        elif time.ticks_diff(time.ticks_ms(), self.last_step_time) > 200:
            self.step_count = 0
    
class InputManager:
    """Manages all input devices and their callbacks."""
    def __init__(self):
        self.encoders = []
        self.buttons = []
        self._init_devices()
        
        # Callback storage
        self._rotation_handlers = []
        self._button_press_handlers = []
        self._button_release_handlers = []
        self._long_press_handlers = []
    
    def _init_devices(self):
        # Initialize encoders
        for enc_id, dt_pin, clk_pin in Pins.ENCODERS:
            encoder = RotaryEncoder(enc_id, dt_pin, clk_pin)
            encoder.rotation_callback = self._handle_rotation
            self.encoders.append(encoder)
        
        # Initialize buttons
        for btn_id, pin_num in Pins.BUTTONS:
            button = Button(btn_id, pin_num)
            button.press_callback = self._handle_button_press
            button.release_callback = self._handle_button_release
            button.long_press_callback = self._handle_long_press
            self.buttons.append(button)
    
    def update(self):
        """Update all input devices."""
        for encoder in self.encoders:
            encoder.update()
        
        for button in self.buttons:
            button.update()
    
    # Event handler registration
    def on_rotation(self, callback):
        """Register a callback for encoder rotation events."""
        self._rotation_handlers.append(callback)
    
    def on_button_press(self, callback):
        """Register a callback for button press events."""
        self._button_press_handlers.append(callback)
    
    def on_button_release(self, callback):
        """Register a callback for button release events."""
        self._button_release_handlers.append(callback)
    
    def on_long_press(self, callback):
        """Register a callback for long press events."""
        self._long_press_handlers.append(callback)
    
    # Internal event handlers
    def _handle_rotation(self, encoder_id, direction, speed):
        for handler in self._rotation_handlers:
            handler(encoder_id, direction, speed)
    
    def _handle_button_press(self, button_id):
        for handler in self._button_press_handlers:
            handler(button_id)
    
    def _handle_button_release(self, button_id):
        for handler in self._button_release_handlers:
            handler(button_id)
    
    def _handle_long_press(self, button_id):
        for handler in self._long_press_handlers:
            handler(button_id)
