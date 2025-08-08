import time
import sys
import select
import machine
from binascii import hexlify
from config import Pins, SerialConfig, ModeConfig, Mode
from input_devices import InputManager
from device import Device, LEDController

class Application:
    def __init__(self):
        # Initialize device components
        self.device = Device()
        self.led = LEDController()
        self.input_manager = InputManager()

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
