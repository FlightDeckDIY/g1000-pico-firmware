# Refactored Main Module - G1P Flight Display Device

import time
import machine
from machine import I2C, Pin
from binascii import hexlify

# Import our modular components
from config import *
from led_controller import LEDController
from mode_manager import ModeManager, PFD_MODE, MFD_MODE
from usb_comm import handle_serial_commands, usb_handler
from mcp23017_handler import MCP23017Handler
from button_handler import ButtonHandler
from encoder_handler import EncoderHandler

# Pre-initialize Pin objects for faster access
button_pins = {}
encoder_pins = {}

def setup_mcu_devices():
    """Initialize MCU pins and store references for fast access."""
    global button_pins, encoder_pins

    for button in BUTTONS:
        button_pins[button[0]] = Pin(button[1], Pin.IN, Pin.PULL_UP)

    for encoder in ENCODERS:
        name, pin_a, pin_b, detent_type = encoder
        encoder_pins[name] = {
            'pin_a': Pin(pin_a, Pin.IN, Pin.PULL_UP),
            'pin_b': Pin(pin_b, Pin.IN, Pin.PULL_UP)
        }

def handle_usb_command(command):
    """Handle incoming USB commands - non-blocking implementation."""
    global mode_manager, led_controller, is_sim_connected

    try:
        if command == "deviceInfo":
            id_hex = hexlify(machine.unique_id()).decode('utf-8')
            print(f"DEVICE ID: {id_hex}")
            print(f"Type: FDD G1P Rev 1 | Mode: {'PFD' if mode_manager.mode == PFD_MODE else 'MFD'}")
            print("Firmware version: 0.1.1\n")

        elif command == "reset":
            print("RESETTING...")
            # Non-blocking reset - schedule for next loop iteration
            global reset_requested
            reset_requested = True

        elif command.startswith("simStatus:"):
            value = command[10:].strip().lower()
            is_sim_connected = value == "connected"
            if led_controller:
                if is_sim_connected:
                    led_controller.stop_breathing()
                    led_controller.brightness = 0
                else:
                    led_controller.start_breathing()
            print(f"SIM_CONNECTED:{is_sim_connected}")

        elif command.lower().startswith("led:") and led_controller is not None:
            value = command[4:].lower()
            try:
                if value == "on":
                    led_controller.enabled = True
                    # print("LED:ON")
                elif value == "off":
                    led_controller.enabled = False
                    # print("LED:OFF")
                elif value == "flash":
                    led_controller.flash()
                    # print("LED:FLASH")
                elif value == "breathe":
                    led_controller.start_breathing()
                    # print("LED:BREATHE")
                elif value == "steady":
                    led_controller.stop_breathing()
                    # print("LED:STEADY")
                else:
                    try:
                        brightness = max(0, min(100, int(value)))
                        led_controller.brightness = brightness
                        # print(f"LED:{brightness}%")
                    except ValueError:
                        print("ERROR:Invalid brightness value")
            except Exception as e:
                print(f"LED_ERROR:{e}")

        elif command.startswith("electricalMaster:") and led_controller is not None:
            value = command[17:].lower()
            # print(f"value", value)
            try:
                if value == "off":
                    led_controller.start_breathing()
                elif value == "on":
                    led_controller.stop_breathing()
            except Exception as e:
                print(f"ELECTRICAL_MASTER_ERROR:{e}")

        elif command.lower() == "encoderstats":
            # Get encoder diagnostic information
            global encoder_handler
            if encoder_handler:
                stats = encoder_handler.get_encoder_stats()
                print(f"ENCODER_STATS:")
                print(f"  Buffer: {stats['buffer_size']}/{encoder_handler.max_buffer_size}")
                print(f"  Overflows: {stats['buffer_overflows']}")
                for name, enc_stats in stats['encoders'].items():
                    print(f"  {name}: detents={enc_stats['total_detents']}, invalid={enc_stats['invalid_transitions']}, speed={enc_stats['last_speed']}")
            else:
                print("ERROR:Encoder handler not initialized")

        elif command.lower() == "resetstats":
            # Reset encoder diagnostic counters
            if encoder_handler:
                encoder_handler.reset_stats()
                print("ENCODER_STATS:RESET")
            else:
                print("ERROR:Encoder handler not initialized")
        else:
            # print(f"UNKNOWN:{command}")
            pass

    except Exception as e:
        print(f"CMD_HANDLER_ERROR:{e}")

def main():
    """Main application loop - optimized and non-blocking."""
    global mode_manager, led_controller, is_sim_connected, reset_requested, encoder_handler

    # Initialize I2C
    i2c = I2C(BUS_ID, scl=Pin(SCL), sda=Pin(SDA), freq=FREQ)

    # Setup mode manager first
    led_controller = LEDController()
    # Register LED flash on mode change
    def on_mode_change(new_mode):
        if new_mode == PFD_MODE:
            led_controller.start_flash(30, 5)
        else:
            led_controller.start_flash(60, 5)
    mode_manager = ModeManager()
    mode_manager.register_mode_change_callback(on_mode_change)
    # Initialize handlers
    mcp_handler = MCP23017Handler(i2c)
    button_handler = ButtonHandler(mode_manager)
    encoder_handler = EncoderHandler(mode_manager, led_controller)
    led_controller.enabled = True
    led_controller.brightness = 15
    led_controller.start_breathing()

    # Setup devices
    setup_mcu_devices()
    if not mcp_handler.setup_devices():
        print("Failed to initialize MCP23017 devices")
        pass

    # Initialize encoder states for MCP encoders with detent types
    from config import MCP_ENCODER_TYPES
    for encoder_pair in mcp_handler.encoder_pairs:
        encoder_name = encoder_pair['name']
        detent_type = MCP_ENCODER_TYPES.get(encoder_name, 'dual')
        encoder_pair['detent_type'] = detent_type

    encoder_handler.initialize_mcp_encoders(mcp_handler.encoder_pairs)

    # Setup interrupts for direct encoders (zero missed detents)
    encoder_handler.setup_interrupts(encoder_pins)

    # (REMOVED DUPLICATE INITIALIZATION)
    # The correct mode_manager and led_controller are already initialized above.
    # Remove this duplicate block to ensure callbacks work as intended.

    # Initialize state variables
    is_sim_connected = False
    is_master_switch_on = False
    reset_requested = False

    # Timing variables
    last_mcp_check = time.ticks_ms()
    last_button_check = time.ticks_ms()
    last_encoder_check = time.ticks_ms()
    last_usb_check = time.ticks_ms()
    last_led_update = time.ticks_ms()

    # Set up USB command handler
    usb_handler.set_command_callback(handle_usb_command)

    # Main loop
    while True:
        current_time = time.ticks_ms()

        # Handle reset request (non-blocking)
        if reset_requested:
            time.sleep_ms(100)  # Brief delay for cleanup
            machine.reset()

        # Process USB communication (every 5ms)
        if time.ticks_diff(current_time, last_usb_check) >= USB_CHECK_INTERVAL:
            last_usb_check = current_time
            handle_serial_commands()

        # Update LED (every 10ms)
        if time.ticks_diff(current_time, last_led_update) >= LED_UPDATE_INTERVAL:
            led_controller.update_flash(current_time)
            if not led_controller._flash_active:
                if not is_sim_connected or not is_master_switch_on:
                    led_controller.breathe()
            last_led_update = current_time

        # Process buffered encoder events (interrupt-driven - highest priority)
        # This processes all encoder events captured by interrupts
        events_processed = encoder_handler.process_buffered_events()

        # Fallback polling for direct encoders (every 1ms) - only if interrupts fail
        if time.ticks_diff(current_time, last_encoder_check) >= ENCODER_CHECK_INTERVAL:
            last_encoder_check = current_time
            # Only use polling as fallback if no interrupt events were processed
            if events_processed == 0:
                encoder_handler.process_direct_encoders_polling(current_time, encoder_pins)

        # Process MCP23017 inputs (every 1ms)
        if time.ticks_diff(current_time, last_mcp_check) >= MCP_CHECK_INTERVAL:
            mcp_handler.process_changes(current_time, button_handler, encoder_handler)
            button_handler.check_map_push_timeout(current_time)
            button_handler.process_mcp_buttons(current_time)
            last_mcp_check = current_time

        # Process button inputs and long press detection (every 20ms)
        if time.ticks_diff(current_time, last_button_check) >= BUTTON_CHECK_INTERVAL:
            last_button_check = current_time
            button_handler.process_long_press_detection(current_time, mode_manager)
            button_handler.process_direct_buttons(current_time, button_pins)

if __name__ == "__main__":
    main()
