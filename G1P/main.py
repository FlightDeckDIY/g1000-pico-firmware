import time
import sys
import select
import machine
from binascii import hexlify
from config import Pins, SerialConfig, ModeConfig, Mode, I2CConfig, ButtonConfig
from input_devices import InputManager, MCP23017
from device import Device, LEDController

class Application:
    def __init__(self):
        # Initialize device components
        self.device = Device()
        self.led = LEDController()
        self.input_manager = InputManager()

        # Initialize I2C and MCP23017 expanders (mirrored open-drain INT)
        self.i2c = I2CConfig.init()
        # Scan for present devices and only init those we find
        scan = self.i2c.scan()
        print(f"I2C_SCAN:{[hex(a) for a in scan]}\n")
        self._mcp_addrs = [a for a in MCP23017.Addr.ALL if a in scan]
        print(f"MCP_ACTIVE:{[hex(a) for a in self._mcp_addrs]}\n")
        # Mapping of expander pins to names/types (currently for 0x22)
        self._mcp_maps = {
            MCP23017.Addr.RIGHT1: {
                'A': {
                    0: ('PROC', 'BUTTON'),
                    1: ('CLR', 'BUTTON'),
                    2: ('DIRECT_TO', 'BUTTON'),
                    3: ('CRS_BARO_CW_1', 'ENCODER'),
                    4: ('CRS_BARO_CCW_1', 'ENCODER'),
                    5: ('CRS_BARO_PUSH', 'BUTTON'),
                    6: ('CRS_BARO_CW_2', 'ENCODER'),
                    7: ('CRS_BARO_CCW_2', 'ENCODER'),
                },
                'B': {
                    0: ('FPL', 'BUTTON'),
                    1: ('MENU', 'BUTTON'),
                    2: ('ENT', 'BUTTON'),
                    3: ('FMS_CW_1', 'ENCODER'),
                    4: ('FMS_CCW_1', 'ENCODER'),
                    5: ('FMS_CW_2', 'ENCODER'),
                    6: ('FMS_PUSH', 'BUTTON'),
                    7: ('FMS_CCW_2', 'ENCODER'),  # confirmed ENCODER
                },
            },
            MCP23017.Addr.RIGHT2: {
                'A': {
                    0: ('MAP_RIGHT', 'BUTTON'),
                    1: ('MAP_ENCODER_A', 'ENCODER'),
                    2: ('COM_SWAP', 'BUTTON'),
                    3: ('COM_FQ_CCW_1', 'ENCODER'),
                    4: ('COM_FQ_CW_1', 'ENCODER'),
                    5: ('COM_FQ_PUSH', 'BUTTON'),
                    6: ('COM_FQ_CW_2', 'ENCODER'),
                    7: ('COM_FQ_CCW_2', 'ENCODER'),
                },
                'B': {
                    0: ('COM_VOL_A', 'ENCODER'),
                    1: ('COM_VOL_B', 'ENCODER'),
                    2: ('COM_VOL_PUSH', 'BUTTON'),
                    3: ('MAP_UP', 'BUTTON'),
                    4: ('MAP_PUSH', 'BUTTON'),
                    5: ('MAP_LEFT', 'BUTTON'),
                    6: ('MAP_ENCODER_B', 'ENCODER'),
                    7: ('MAP_DOWN', 'BUTTON'),  # assumed BUTTON
                },
            },
        }
        for a in self._mcp_addrs:
            try:
                MCP23017.configure_interrupt_mirror(self.i2c, a, mirror=True, open_drain=True)
                # Configure inputs + interrupt-on-change for the 0x22 device per mapping
                if a == MCP23017.Addr.RIGHT1:
                    # Enable interrupts on: all buttons, and only *_1 encoder lines for single event per detent
                    gpinten_a = 0x3F  # A0..A5 enabled; A6/A7 (CRS_BARO_*_2) disabled
                    gpinten_b = 0x5F  # B0..B4,B6 enabled; B5/B7 (FMS_*_2) disabled
                    # Use change-detect on all pins; we'll filter encoders to falling edge in software
                    intcon_a = 0x00
                    intcon_b = 0x00
                    defval_a = 0x00
                    defval_b = 0x00
                    MCP23017.configure_inputs_interrupt_on_change(
                        self.i2c,
                        a,
                        iodir_a=0xFF, iodir_b=0xFF,
                        pullups_a=0xFF, pullups_b=0xFF,
                        gpinten_a=gpinten_a, gpinten_b=gpinten_b,
                        intcon_a=intcon_a, intcon_b=intcon_b,
                        defval_a=defval_a, defval_b=defval_b,
                    )
                # Configure inputs + interrupt-on-change for the 0x24 device per mapping
                if a == MCP23017.Addr.RIGHT2:
                    # Enable interrupts on: buttons and only one phase per encoder
                    # A side: enable buttons (A0,A2,A5) and encoder lines A1, A3, A4; disable A6,A7 (COM_FQ *_2)
                    gpinten_a = 0x3F  # 0b0011_1111
                    # B side: enable COM_VOL_A (B0) as primary phase, buttons B2,B3,B4,B5,B7; disable B1,B6
                    gpinten_b = 0xBD  # 0b1011_1101
                    # Use change-detect; filter encoders in software to falling edge only
                    intcon_a = 0x00
                    intcon_b = 0x00
                    defval_a = 0x00
                    defval_b = 0x00
                    MCP23017.configure_inputs_interrupt_on_change(
                        self.i2c,
                        a,
                        iodir_a=0xFF, iodir_b=0xFF,
                        pullups_a=0xFF, pullups_b=0xFF,
                        gpinten_a=gpinten_a, gpinten_b=gpinten_b,
                        intcon_a=intcon_a, intcon_b=intcon_b,
                        defval_a=defval_a, defval_b=defval_b,
                    )
            except Exception as e:
                print("WARN:MCP23017 init at {} failed: {}".format(hex(a), e))
        # Shared interrupt line on GPIO1
        self._mcp_int_flag = False
        self._mcp_irq_count = 0
        self._mcp_int_pin = MCP23017.setup_shared_int_pin(callback=self._on_mcp_int, trigger=machine.Pin.IRQ_FALLING)
        self._mcp_int_state = self._mcp_int_pin.value()
        self._last_mcp_poll = time.ticks_ms()
        # Debounce tracking for MCP events
        self._mcp_last_event_ms = {}
        self._encoder_debounce_ms = 10
        # Encoder edge gating: ensure we only emit once per low phase until release
        self._enc_active = set()  # keys of form (addr, 'A'|'B', bit)
        # Debug verbosity for IRQ count prints
        self._mcp_debug = False

        # Command buffer for serial input
        self.command_buffer = ""

        # Set up event handlers
        self._setup_event_handlers()

        # Initial LED state
        self.led.enabled = True
        self.is_sim_connected = False
        self.led.brightness = 92  # 92% brightness. This is the default in MSFS 2024

        print("\n=== G1P Controller Initialized ===")
        print(f"Mode: {self.device.mode}")

    def _on_mcp_int(self, pin):
        # Minimal ISR: set a flag for main loop to poll expanders
        self._mcp_int_flag = True
        self._mcp_irq_count += 1

    def _setup_event_handlers(self):
        # Button press/release handlers
        self.input_manager.on_button_press(self._handle_button_press)
        self.input_manager.on_button_release(self._handle_button_release)
        self.input_manager.on_long_press(self._handle_long_press)
        self.input_manager.on_rotation(self._handle_rotation)

        # Mode change handler
        self.device.on_mode_change(self._handle_mode_change)

    def _handle_button_press(self, button_id):
        """Handle button press events."""

        # Send button press event
        msg = SerialConfig.Messages.BUTTON.format(
            prefix=SerialConfig.MSG_PREFIX,
            id=button_id,
            action="PRESS"
        )
        print(f"{msg}\n")

    def _handle_button_release(self, button_id):
        """Handle button release events."""

        msg = SerialConfig.Messages.BUTTON.format(
            prefix=SerialConfig.MSG_PREFIX,
            id=button_id,
            action="RELEASE"
        )
        print(f"{msg}\n")

    def _handle_long_press(self, button_id):
        """Handle long press events."""
        if button_id == ModeConfig.MODE_SWITCH_BUTTON:
            # Toggle operating mode
            self.device.toggle_mode()

    def _handle_rotation(self, encoder_id, direction, speed):
        """Handle encoder rotation events."""
        msg = SerialConfig.Messages.ROTARY.format(
            prefix=SerialConfig.MSG_PREFIX,
            id=encoder_id,
            direction="CW" if direction > 0 else "CCW",
            speed=speed
        )
        print(f"{msg}\n")

    def _handle_mode_change(self, new_mode):
        """Handle mode change events."""
        # Visual feedback for mode change. Fast flash for PFD, slow flash for MFD
        if new_mode == Mode.PFD:
            self.led.flash()
        elif new_mode == Mode.MFD:
            self.led.flash(100, 5)

        # Send mode change event
        msg = SerialConfig.Messages.MODE_CHANGE.format(
            prefix=SerialConfig.MSG_PREFIX,
            mode=Mode.name(new_mode)
        )
        print(f"{msg}\n")

    def check_serial_commands(self):
        """Check for incoming serial commands."""
        try:
            poller = select.poll()
            poller.register(sys.stdin, select.POLLIN)

            if poller.poll(0):  # Check if there's data available (0 timeout)
                line = sys.stdin.readline().strip()

                if line == "deviceId":
                    # Return the device ID
                    id_hex = hexlify(machine.unique_id()).decode('utf-8')
                    print(f"DEVICE_ID:{id_hex}\n")

                if line.startswith("simStatus:"):
                    try:
                        value = line[10:].strip().lower()
                        was_connected = self.is_sim_connected
                        self.is_sim_connected = value == "connected"

                        # If we just connected, set LED to 92%
                        if self.is_sim_connected and not was_connected:
                            self.led.brightness = 92
                            self.led.enabled = True
                        print(f"SIM_CONNECTED:{self.is_sim_connected}\n")
                    except (ValueError, IndexError) as e:
                        print(f"ERROR: Invalid simStatus command: {e}\n")

                elif line == "reset":
                    # Reset the device
                    print("RESETTING...\n")
                    time.sleep(1)
                    machine.reset()

                elif line.startswith("led="):
                    # Control the LED: led=on/off or led=50 (0-100%)
                    try:
                        value = line[4:].lower()
                        if value == "on":
                            self.led.enabled = True
                            print("LED:ON\n")
                        elif value == "off":
                            self.led.enabled = False
                            print("LED:OFF\n")
                        else:
                            brightness = int(value)
                            self.led.brightness = brightness
                            print(f"LED:{brightness}%\n")
                    except (ValueError, IndexError):
                        print("ERROR: Invalid LED command\n")

                else:
                    # Echo back unknown commands
                    print(f"UNKNOWN:{line}\n")

        except Exception as e:
            print(f"ERROR:{str(e)}\n")

    def run(self):
        """Main application loop."""
        last_led_update = time.ticks_ms()

        while True:
            current_time = time.ticks_ms()

            # Update input devices
            self.input_manager.update()

            # Handle MCP23017 shared interrupt events (polling to identify source)
            if self._mcp_int_flag:
                self._mcp_int_flag = False
                loops = 0
                while self._mcp_int_pin.value() == 0 and loops < 8:
                    any_event = False
                    for a in getattr(self, "_mcp_addrs", []):
                        try:
                            fa, ca, fb, cb = MCP23017.read_and_clear_interrupts(self.i2c, a)
                            if fa or fb:
                                any_event = True
                                mapping = getattr(self, "_mcp_maps", {}).get(a)
                                if mapping:
                                    if fa:
                                        for bit in range(8):
                                            if fa & (1 << bit):
                                                name, typ = mapping['A'].get(bit, (f"A{bit}", "IN"))
                                                now = time.ticks_ms()
                                                key = (a, 'A', bit)
                                                thresh = ButtonConfig.DEBOUNCE_MS if typ == 'BUTTON' else self._encoder_debounce_ms
                                                last = self._mcp_last_event_ms.get(key, 0)
                                                if time.ticks_diff(now, last) >= thresh:
                                                    self._mcp_last_event_ms[key] = now
                                                    val = (ca >> bit) & 1
                                                    if typ == 'ENCODER':
                                                        if val == 0:
                                                            if key in self._enc_active:
                                                                continue
                                                            self._enc_active.add(key)
                                                            print(f"{SerialConfig.MSG_PREFIX}:MCP:{hex(a)}:A:{name}:{typ}:{val}\n")
                                                        else:
                                                            if key in self._enc_active:
                                                                self._enc_active.remove(key)
                                                            continue
                                                    else:
                                                        print(f"{SerialConfig.MSG_PREFIX}:MCP:{hex(a)}:A:{name}:{typ}:{val}\n")
                                    if fb:
                                        for bit in range(8):
                                            if fb & (1 << bit):
                                                name, typ = mapping['B'].get(bit, (f"B{bit}", "IN"))
                                                now = time.ticks_ms()
                                                key = (a, 'B', bit)
                                                thresh = ButtonConfig.DEBOUNCE_MS if typ == 'BUTTON' else self._encoder_debounce_ms
                                                last = self._mcp_last_event_ms.get(key, 0)
                                                if time.ticks_diff(now, last) >= thresh:
                                                    self._mcp_last_event_ms[key] = now
                                                    val = (cb >> bit) & 1
                                                    if typ == 'ENCODER':
                                                        if val == 0:
                                                            if key in self._enc_active:
                                                                continue
                                                            self._enc_active.add(key)
                                                            print(f"{SerialConfig.MSG_PREFIX}:MCP:{hex(a)}:B:{name}:{typ}:{val}\n")
                                                        else:
                                                            if key in self._enc_active:
                                                                self._enc_active.remove(key)
                                                            continue
                                                    else:
                                                        print(f"{SerialConfig.MSG_PREFIX}:MCP:{hex(a)}:B:{name}:{typ}:{val}\n")
                                else:
                                    # Fallback: print raw summary
                                    print(f"{SerialConfig.MSG_PREFIX}:MCP_INT:{hex(a)}:A:flags=0x{fa:02X},cap=0x{ca:02X}\n")
                                    print(f"{SerialConfig.MSG_PREFIX}:MCP_INT:{hex(a)}:B:flags=0x{fb:02X},cap=0x{cb:02X}\n")
                        except Exception as e:
                            print(f"WARN:MCP23017 poll {hex(a)} failed:{e}\n")
                    loops += 1
                    if not any_event:
                        break
                if getattr(self, "_mcp_debug", False):
                    print(f"{SerialConfig.MSG_PREFIX}:MCP_IRQ_COUNT:{self._mcp_irq_count}\n")

            # Periodic fallback poll in case the INT IRQ is not firing
            if time.ticks_diff(current_time, getattr(self, "_last_mcp_poll", 0)) >= 20:
                self._last_mcp_poll = current_time
                # INT pin state change diagnostic
                cur = self._mcp_int_pin.value()
                if cur != self._mcp_int_state:
                    self._mcp_int_state = cur
                    print(f"{SerialConfig.MSG_PREFIX}:MCP_INT_PIN:{cur}\n")
                if cur == 0:  # only poll expanders if INT is asserted
                    loops = 0
                    while cur == 0 and loops < 8:
                        for a in getattr(self, "_mcp_addrs", []):
                            try:
                                fa, ca, fb, cb = MCP23017.read_and_clear_interrupts(self.i2c, a)
                                if fa or fb:
                                    mapping = getattr(self, "_mcp_maps", {}).get(a)
                                    if mapping:
                                        if fa:
                                            for bit in range(8):
                                                if fa & (1 << bit):
                                                    name, typ = mapping['A'].get(bit, (f"A{bit}", "IN"))
                                                    now = time.ticks_ms()
                                                    key = (a, 'A', bit)
                                                    thresh = ButtonConfig.DEBOUNCE_MS if typ == 'BUTTON' else self._encoder_debounce_ms
                                                    last = self._mcp_last_event_ms.get(key, 0)
                                                    if time.ticks_diff(now, last) >= thresh:
                                                        self._mcp_last_event_ms[key] = now
                                                        val = (ca >> bit) & 1
                                                        if typ == 'ENCODER':
                                                            if val == 0:
                                                                if key in self._enc_active:
                                                                    continue
                                                                self._enc_active.add(key)
                                                                print(f"{SerialConfig.MSG_PREFIX}:MCP:{hex(a)}:A:{name}:{typ}:{val}\n")
                                                            else:
                                                                if key in self._enc_active:
                                                                    self._enc_active.remove(key)
                                                                continue
                                                        else:
                                                            print(f"{SerialConfig.MSG_PREFIX}:MCP:{hex(a)}:A:{name}:{typ}:{val}\n")
                                        if fb:
                                            for bit in range(8):
                                                if fb & (1 << bit):
                                                    name, typ = mapping['B'].get(bit, (f"B{bit}", "IN"))
                                                    now = time.ticks_ms()
                                                    key = (a, 'B', bit)
                                                    thresh = ButtonConfig.DEBOUNCE_MS if typ == 'BUTTON' else self._encoder_debounce_ms
                                                    last = self._mcp_last_event_ms.get(key, 0)
                                                    if time.ticks_diff(now, last) >= thresh:
                                                        self._mcp_last_event_ms[key] = now
                                                        val = (cb >> bit) & 1
                                                        if typ == 'ENCODER':
                                                            if val == 0:
                                                                if key in self._enc_active:
                                                                    continue
                                                                self._enc_active.add(key)
                                                                print(f"{SerialConfig.MSG_PREFIX}:MCP:{hex(a)}:B:{name}:{typ}:{val}\n")
                                                            else:
                                                                if key in self._enc_active:
                                                                    self._enc_active.remove(key)
                                                                continue
                                                        else:
                                                            print(f"{SerialConfig.MSG_PREFIX}:MCP:{hex(a)}:B:{name}:{typ}:{val}\n")
                                    else:
                                        print(f"{SerialConfig.MSG_PREFIX}:MCP_INT:{hex(a)}:A:flags=0x{fa:02X},cap=0x{ca:02X}\n")
                                        print(f"{SerialConfig.MSG_PREFIX}:MCP_INT:{hex(a)}:B:flags=0x{fb:02X},cap=0x{cb:02X}\n")
                            except Exception as e:
                                print(f"WARN:MCP23017 poll {hex(a)} failed:{e}\n")
                        loops += 1
                        cur = self._mcp_int_pin.value()

            # Check for serial commands
            self.check_serial_commands()

            # Update LED (for any animations or effects)
            if time.ticks_diff(current_time, last_led_update) > 10:  # 100Hz
                if not self.is_sim_connected:
                    # Run breathing animation when sim is not connected
                    self.led.breathe()
                # When sim is connected, the brightness is set to 92% in the simStatus handler
                # and will stay there until the connection is lost
                last_led_update = current_time

            # Small delay to prevent CPU overload
            time.sleep_ms(1)

def main():
    # Create and run the application
    app = Application()
    app.run()

if __name__ == "__main__":
    main()
