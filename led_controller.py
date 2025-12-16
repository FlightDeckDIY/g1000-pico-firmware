import machine
import time
# from config import LED_BACKLIGHT

# LED backlighting pin
LED_BACKLIGHT = 21

class LEDController:
    """Controls the LED backlight."""
    
    def __init__(self):
        self.pin = machine.Pin(LED_BACKLIGHT, machine.Pin.OUT)
        self._brightness = 0  # 0-100%
        self._enabled = False
        
        # Initialize PWM for brightness control
        self.pwm = machine.PWM(self.pin)
        self.pwm.freq(1000)  # 1kHz PWM frequency

        self.last_update = time.ticks_ms()
        self._breathing = False
        # Flash state
        self._flash_active = False
        self._flash_count = 0
        self._flash_total = 0
        self._flash_on = False
        self._flash_next_time = 0
        self._flash_duration_ms = 0
        self._flash_brightness_override = None

        self.update()

    def start_flash(self, duration_ms=30, number_of_flashes=5):
        self._flash_active = True
        self._flash_count = 0
        self._flash_total = number_of_flashes * 2  # on/off cycles
        self._flash_on = False
        self._flash_duration_ms = duration_ms
        self._flash_next_time = time.ticks_ms()
        self._breathing = False  # Suppress breathing during flash
        self._flash_brightness_override = 100
        self.update()

    def update_flash(self, now=None):
        if not self._flash_active:
            return
        now = now if now is not None else time.ticks_ms()
        if time.ticks_diff(now, self._flash_next_time) >= 0:
            self._flash_on = not self._flash_on
            self.enabled = self._flash_on
            self._flash_count += 1
            self._flash_next_time = time.ticks_add(now, self._flash_duration_ms)
            if self._flash_count >= self._flash_total:
                self._flash_active = False
                self.enabled = True
                self._flash_brightness_override = None
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

    def adjust_brightness(self, delta):
        """Increment brightness by delta percent while staying within 0-100."""
        target = self._brightness + int(delta)
        self._brightness = max(0, min(100, target))
        self.update()
        return self._brightness
    
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
        brightness = self._flash_brightness_override if self._flash_brightness_override is not None else self._brightness
        if self._enabled and brightness > 0:
            # Convert 0-100 to 16-bit duty cycle
            duty = int((brightness / 100) * 65535)
            self.pwm.duty_u16(duty)
        else:
            self.pwm.duty_u16(0)
    
    def toggle(self):
        """Toggle the backlight on/off."""
        self.enabled = not self._enabled

    def flash(self, duration_ms=30, number_of_flashes=5):
        """Flash the backlight for a specified duration."""
        previous_override = self._flash_brightness_override
        self._flash_brightness_override = 100
        self.update()
        for _ in range(number_of_flashes):
            self.enabled = True
            time.sleep_ms(duration_ms)
            self.enabled = False
            time.sleep_ms(duration_ms)

        self.enabled = True
        self._flash_brightness_override = previous_override
        self.update()

    def breathe(self, duration_ms=2500, max_brightness=50, min_brightness=10, hold_ms=40):
        """Smooth breathing effect for the LED with a pause at min/max brightness.
        
        Returns:
            bool: True if the animation updated the brightness, False if it should be stopped
        """
        # Only update brightness if we're in breathing mode
        if not hasattr(self, '_breathing') or not self._breathing:
            return False
            
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
        
        self._brightness = int(brightness)
        self.update()
        return True
        
    def start_breathing(self):
        """Start the breathing animation."""
        self._breathing = True
        
    def stop_breathing(self):
        """Stop the breathing animation."""
        self._breathing = False
        
