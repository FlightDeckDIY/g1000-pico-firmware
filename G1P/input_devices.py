from machine import Pin, I2C, Timer
import time
import micropython
from config import (
    Pins, ButtonConfig, EncoderConfig, 
    ModeConfig, SerialConfig, I2CConfig
)

# Allocate memory for interrupt handlers
micropython.alloc_emergency_exception_buf(100)

#-------------------------------------------------------------------------------------
# Button
#-------------------------------------------------------------------------------------

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

#----------------------------------------------------------------------------------------------------
# Rotary Encoder
#----------------------------------------------------------------------------------------------------

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
            # Only act on rising edge to avoid double counts per detent
            if current_clk == 1:
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
            
            # Update last_clk after handling edge (rising or falling)
            self.last_clk = current_clk
        
        # Reset step count if no movement for a while
        elif time.ticks_diff(time.ticks_ms(), self.last_step_time) > 200:
            self.step_count = 0

#----------------------------------------------------------------------------------------------------
# Input Manager
#----------------------------------------------------------------------------------------------------
    
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

#----------------------------------------------------------------------------------------------------
# MCP23017 GPIO Expander (moved from config.py)
#----------------------------------------------------------------------------------------------------

class MCP23017:
    """Helpers and constants for configuring MCP23017 expanders."""

    class Addr:
        BOTTOM = 0x20  # bottom PCB
        RIGHT1 = 0x22  # right PCB (first)
        RIGHT2 = 0x24  # right PCB (second)
        ALL = [BOTTOM, RIGHT1, RIGHT2]

    class Reg:
        IODIRA   = 0x00
        IODIRB   = 0x01
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

    class IOCONBits:
        BANK   = 0x80
        MIRROR = 0x40  # Mirror INTA/INTB
        SEQOP  = 0x20
        DISSLW = 0x10
        HAEN   = 0x08  # not used on MCP23017 (I2C)
        ODR    = 0x04  # Open-drain INT output
        INTPOL = 0x02  # Interrupt polarity (ignored if ODR=1)

    @staticmethod
    def _read_reg(i2c, addr, reg, n=1):
        return i2c.readfrom_mem(addr, reg, n)

    @staticmethod
    def _write_reg(i2c, addr, reg, data):
        i2c.writeto_mem(addr, reg, data)

    @staticmethod
    def configure_interrupt_mirror(i2c, addr, *, mirror=True, open_drain=True, intpol_high=False):
        """Enable mirrored interrupts between PortA and PortB and set INT pin mode.
        - mirror=True ties INTA/INTB together internally so either port asserts the single INT line.
        - open_drain=True is recommended when multiple MCP23017 INT pins are wired together.
        - intpol_high sets active-high polarity when open_drain is False.
        """
        current = MCP23017._read_reg(i2c, addr, MCP23017.Reg.IOCON, 1)[0]
        # Set/clear MIRROR
        if mirror:
            current |= MCP23017.IOCONBits.MIRROR
        else:
            current &= ~MCP23017.IOCONBits.MIRROR
        # Configure INT output mode
        if open_drain:
            current |= MCP23017.IOCONBits.ODR
            # INTPOL is ignored when ODR=1
        else:
            current &= ~MCP23017.IOCONBits.ODR
            if intpol_high:
                current |= MCP23017.IOCONBits.INTPOL
            else:
                current &= ~MCP23017.IOCONBits.INTPOL
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.IOCON, bytes([current]))

    @staticmethod
    def init_all_for_shared_interrupt(i2c=None):
        """Initialize all MCP23017 devices (0x20, 0x22, 0x24) to use mirrored, open-drain INT outputs.
        Returns the I2C instance used.
        """
        if i2c is None:
            i2c = I2CConfig.init()
        for a in MCP23017.Addr.ALL:
            try:
                MCP23017.configure_interrupt_mirror(i2c, a, mirror=True, open_drain=True)
            except Exception as e:
                # Device might be absent during bring-up; continue with others
                print("WARN:MCP23017 init failed at 0x{:02X}: {}".format(a, e))
        return i2c

    @staticmethod
    def setup_shared_int_pin(callback=None, *, trigger=Pin.IRQ_FALLING):
        """Configure the shared INT line from all MCP23017s on a single MCU pin.
        Uses GPIO1 with internal pull-up. Optionally attach an IRQ callback.
        """
        pin = Pin(Pins.MCP_INT, Pin.IN, Pin.PULL_UP)
        if callback is not None:
            pin.irq(trigger=trigger, handler=callback)
        return pin

    @staticmethod
    def read_and_clear_interrupts(i2c, addr):
        """Read interrupt flags and capture registers and clear the interrupt.
        Returns a tuple: (flags_a, cap_a, flags_b, cap_b)
        Reading INTCAPx clears the latched interrupt condition on that port.
        """
        try:
            flags_a = MCP23017._read_reg(i2c, addr, MCP23017.Reg.INTFA, 1)[0]
            flags_b = MCP23017._read_reg(i2c, addr, MCP23017.Reg.INTFB, 1)[0]
            cap_a = MCP23017._read_reg(i2c, addr, MCP23017.Reg.INTCAPA, 1)[0]
            cap_b = MCP23017._read_reg(i2c, addr, MCP23017.Reg.INTCAPB, 1)[0]
            return flags_a, cap_a, flags_b, cap_b
        except Exception as e:
            raise e

    @staticmethod
    def configure_inputs_interrupt_on_change(
        i2c,
        addr,
        *,
        iodir_a=0xFF,
        iodir_b=0xFF,
        pullups_a=0xFF,
        pullups_b=0xFF,
        gpinten_a=0xFF,
        gpinten_b=0xFF,
        intcon_a=0x00,
        intcon_b=0x00,
        defval_a=0x00,
        defval_b=0x00,
    ):
        """Configure selected pins as inputs with pull-ups and interrupt-on-change.
        - iodir_x: 1 bit = input, 0 bit = output
        - pullups_x: enable internal 100k pull-ups for input pins
        - gpinten_x: enable interrupt-on-change for those pins
        - intcon_x: 0 = compare to previous value (change detect), 1 = compare to DEFVAL
        - defval_x: compare reference when intcon bit=1
        """
        # Directions
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.IODIRA, bytes([iodir_a]))
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.IODIRB, bytes([iodir_b]))
        # Pull-ups
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.GPPUA, bytes([pullups_a]))
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.GPPUB, bytes([pullups_b]))
        # Interrupt control
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.INTCONA, bytes([intcon_a]))
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.INTCONB, bytes([intcon_b]))
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.DEFVALA, bytes([defval_a]))
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.DEFVALB, bytes([defval_b]))
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.GPINTENA, bytes([gpinten_a]))
        MCP23017._write_reg(i2c, addr, MCP23017.Reg.GPINTENB, bytes([gpinten_b]))
        # Clear any pending by reading INTCAP
        try:
            MCP23017._read_reg(i2c, addr, MCP23017.Reg.INTCAPA, 1)
            MCP23017._read_reg(i2c, addr, MCP23017.Reg.INTCAPB, 1)
        except Exception:
            pass
