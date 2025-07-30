import machine
import ustruct
import os
from config import ModeConfig, SerialConfig

class Device:
    """Manages device state including operating mode and EEPROM storage."""
    
    def __init__(self):
        # Initialize filesystem for persistent storage
        self._mode_file = 'mode.dat'
        self._mode = self._load_mode()
        self._mode_change_callback = None
    
    def _load_mode(self):
        """Load the operating mode from filesystem."""
        try:
            # Try to read mode from file
            if self._mode_file in os.listdir():
                with open(self._mode_file, 'r') as f:
                    mode = int(f.read().strip())
                    if mode in (0, 1):
                        return mode
        except Exception as e:
            print(f"Error reading mode from filesystem: {e}")
        
        # Return default mode if reading fails
        return ModeConfig.MODE_DEFAULT
    
    def _save_mode(self, mode):
        """Save the operating mode to filesystem."""
        try:
            # Ensure we have a valid mode (0 or 1)
            mode = 1 if mode else 0
            
            # Write mode to file
            with open(self._mode_file, 'w') as f:
                f.write(str(mode))
            return True
        except Exception as e:
            print(f"Error writing mode to filesystem: {e}")
            return False
    
    @property
    def mode(self):
        """Get the current operating mode."""
        return self._mode
    
    @mode.setter
    def mode(self, new_mode):
        """Set a new operating mode and save it to EEPROM."""
        if new_mode not in (0, 1):
            raise ValueError("Mode must be 0 or 1")
        
        if new_mode != self._mode:
            self._mode = new_mode
            self._save_mode(new_mode)
            
            # Notify about mode change
            if self._mode_change_callback:
                self._mode_change_callback(new_mode)
    
    def toggle_mode(self):
        """Toggle between the two operating modes."""
        self.mode = 1 - self._mode
    
    def on_mode_change(self, callback):
        """Register a callback for mode change events."""
        self._mode_change_callback = callback

class LEDController:
    """Controls the LED backlight."""
    
    def __init__(self, pin_num):
        self.pin = machine.Pin(pin_num, machine.Pin.OUT)
        self._brightness = 0  # 0-100%
        self._enabled = False
        
        # Initialize PWM for brightness control
        self.pwm = machine.PWM(self.pin)
        self.pwm.freq(1000)  # 1kHz PWM frequency
        self.update()
    
    @property
    def brightness(self):
        """Get the current brightness (0-100)."""
        return self._brightness
    
    @brightness.setter
    def brightness(self, value):
        """Set the brightness (0-100)."""
        self._brightness = max(0, min(100, int(value)))
        self.update()
    
    @property
    def enabled(self):
        """Check if the backlight is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value):
        """Enable or disable the backlight."""
        self._enabled = bool(value)
        self.update()
    
    def update(self):
        """Update the PWM output based on current settings."""
        if self._enabled and self._brightness > 0:
            # Convert 0-100 to 16-bit duty cycle
            duty = int((self._brightness / 100) * 65535)
            self.pwm.duty_u16(duty)
        else:
            self.pwm.duty_u16(0)
    
    def toggle(self):
        """Toggle the backlight on/off."""
        self.enabled = not self._enabled
