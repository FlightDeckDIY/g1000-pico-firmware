import machine
import os
from config import ModeConfig, Mode, Pins
import time


#-------------------------------------------------------------------------------------
# Device
#-------------------------------------------------------------------------------------

class Device:
    """Manages device state including operating mode and saved configuration."""
    
    def __init__(self):
        # Initialize filesystem for persistent storage
        self._mode_file = 'mode.dat'
        self._mode = self._load_mode()
        self._mode_change_callback = None
    
    def _load_mode(self):
        """Load the operating mode from filesystem as Mode const (int)."""
        try:
            # Try to read mode from file
            if self._mode_file in os.listdir():                 # list all files in the current directory (root)
                with open(self._mode_file, 'r') as f:           # opens the file in read mode ('r')
                    mode_val = int(f.read().strip())            # read the file and strip any leading/trailing whitespace
                    if mode_val in (Mode.PFD, Mode.MFD):        # check if the mode value is valid (integer representing Mode.PFD or Mode.MFD)
                        return mode_val
        except Exception as e:
            print(f"Error reading mode from filesystem: {e}")
        
        # Return default mode if reading fails
        return ModeConfig.MODE_DEFAULT
    
    def _save_mode(self, mode):
        """Save the operating mode to filesystem as Mode const (int)."""
        try:
            # Ensure we have a valid mode (int)
            if mode not in (Mode.PFD, Mode.MFD):
                raise ValueError("mode must be Mode.PFD or Mode.MFD")
            # Write mode value to file
            with open(self._mode_file, 'w') as f:             # open file for writing
                f.write(str(mode))
            return True
        except Exception as e:
            print(f"Error writing mode to filesystem: {e}")
            return False
    
    @property
    def mode(self):
        """Get the current operating mode as a Mode const (int)."""
        return self._mode
    
    @mode.setter
    def mode(self, new_mode):
        """Set a new operating mode and save it to filesystem."""
        if new_mode not in (Mode.PFD, Mode.MFD):
            raise ValueError("Mode must be Mode.PFD or Mode.MFD")
        if new_mode != self._mode:                           # if the new mode is different from the current mode
            self._mode = new_mode
            self._save_mode(new_mode)                       # save the new mode to the filesystem
            # Notify about mode change
            if self._mode_change_callback:
                self._mode_change_callback(new_mode)
    
    def toggle_mode(self):
        """Toggle between the two operating modes."""
        self.mode = Mode.MFD if self._mode == Mode.PFD else Mode.PFD
    
    def on_mode_change(self, callback):
        """Register a callback for mode change events."""
        self._mode_change_callback = callback



#----------------------------------------------------------------------------------------------------
# LED Controller
#----------------------------------------------------------------------------------------------------

class LEDController:
    """Controls the LED backlight."""
    
    def __init__(self):
        self.pin = machine.Pin(Pins.LED_BACKLIGHT, machine.Pin.OUT)
        self._brightness = 0  # 0-100%
        self._enabled = False
        
        # Initialize PWM for brightness control
        self.pwm = machine.PWM(self.pin)
        self.pwm.freq(1000)  # 1kHz PWM frequency

        self.last_update = time.ticks_ms()

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

    def flash(self, duration_ms=30, number_of_flashes=5):
        """Flash the backlight for a specified duration."""
        for _ in range(number_of_flashes):
            self.enabled = True
            time.sleep_ms(duration_ms)
            self.enabled = False
            time.sleep_ms(duration_ms)

        self.enabled = True

    def breathe(self, duration_ms=3000, max_brightness=50, min_brightness=15, hold_ms=40):
        """Smooth breathing effect for the LED with a pause at min/max brightness."""
        current_time = time.ticks_ms()
        half_duration = (duration_ms - (2 * hold_ms)) / 2  # Time for each fade in/out
        cycle_duration = duration_ms  # Total time for one full cycle
        
        # Calculate elapsed time within the current cycle
        elapsed = time.ticks_diff(current_time, self.last_update) % cycle_duration
        
        if elapsed < half_duration:
            # Fading in
            progress = elapsed / half_duration
            brightness = min_brightness + (progress * (max_brightness - min_brightness))
        elif elapsed < half_duration + hold_ms:
            # Hold at max brightness
            brightness = max_brightness
        elif elapsed < (2 * half_duration) + hold_ms:
            # Fading out
            progress = (elapsed - half_duration - hold_ms) / half_duration
            brightness = max_brightness - (progress * (max_brightness - min_brightness))
        else:
            # Hold at min brightness
            brightness = min_brightness
        
        self.brightness = int(brightness)
        
        
        