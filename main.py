# Refactored Main Module - G1P Flight Display Device

import time
import machine
from machine import I2C, Pin
from binascii import hexlify

# Transport selection: default to CDC serial (existing behavior). Set
# this to True in a HID-capable build when hid_transport is wired up.
USE_HID_TRANSPORT = False

# Import our modular components
from config import *
from led_controller import LEDController
from mode_manager import ModeManager, PFD_MODE, MFD_MODE
from usb_comm import handle_serial_commands, usb_handler
from mcp23017_handler import MCP23017Handler
from button_handler import ButtonHandler
from encoder_handler import EncoderHandler
from command_router import CommandRouter

# Pre-initialize Pin objects for faster access
button_pins = {}
encoder_pins = {}

# Global command router instance (initialized in main())
command_router = None

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
    """Handle incoming USB commands via the protocol/command router.

    This function now uses the text protocol adapter to decode the
    incoming ASCII command into a message, then routes it through the
    CommandRouter, and finally prints any text responses to preserve
    existing CDC behavior.
    """
    global mode_manager, led_controller, is_sim_connected, command_router

    from protocol_text import decode_text_command, encode_text_responses
    from protocol_ids import (
        MSG_SIM_STATUS_UPDATE,
        MSG_ENCODER_STATS_RESPONSE,
    )

    try:
        # Decode the textual command into a high-level message.
        msg = decode_text_command(command)
        if msg is None:
            # Unknown/ignored command – preserve existing behavior of
            # doing nothing.
            return

        # For simStatus updates, we still want to emit a
        # SIM_CONNECTED:<bool> line for compatibility. We handle that
        # after routing.
        is_sim_status_update = (msg.get("type") == MSG_SIM_STATUS_UPDATE)

        # Route the message through the command router.
        if command_router is None:
            # Safety fallback: if router isn't initialized, just ignore.
            return

        responses = command_router.handle_message(msg) or []

        # Format any structured responses (e.g., deviceInfo,
        # encoderStats) back into text lines.
        lines = encode_text_responses(responses, mode_manager=mode_manager)
        for line in lines:
            print(line)

        # Special-case behaviors that previously printed directly in
        # handle_usb_command:
        if is_sim_status_update:
            # The router callback updates is_sim_connected and LED
            # state; we only need to mirror the SIM_CONNECTED line.
            print("SIM_CONNECTED:{}".format(is_sim_connected))

        # For encoder stats reset, we previously printed a static line.
        # The host triggers that via the "resetstats" command.
        if command.strip().lower() == "resetstats":
            # If encoder_handler exists, the router already reset stats.
            # We just mirror the confirmation text.
            from __main__ import encoder_handler  # avoid circular import at top
            if encoder_handler:
                print("ENCODER_STATS:RESET")
            else:
                print("ERROR:Encoder handler not initialized")

    except Exception as e:
        print("CMD_HANDLER_ERROR:{}".format(e))

def main():
    """Main application loop - optimized and non-blocking."""
    global mode_manager, led_controller, is_sim_connected, reset_requested, encoder_handler, command_router

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

    # Create callbacks for CommandRouter so it can update
    # connection/reset state without touching globals directly.
    def set_sim_connected(connected):
        nonlocal is_sim_connected
        is_sim_connected = connected
        # Mirror previous LED behavior for simStatus:
        if led_controller:
            if is_sim_connected:
                led_controller.stop_breathing()
                led_controller.brightness = 0
            else:
                led_controller.start_breathing()

    def request_reset():
        nonlocal reset_requested
        print("RESETTING...")
        reset_requested = True

    # Initialize command router
    command_router = CommandRouter(
        mode_manager=mode_manager,
        led_controller=led_controller,
        encoder_handler=encoder_handler,
        set_sim_connected_cb=set_sim_connected,
        request_reset_cb=request_reset,
        firmware_version="0.1.1",
    )

    # Timing variables
    last_mcp_check = time.ticks_ms()
    last_button_check = time.ticks_ms()
    last_encoder_check = time.ticks_ms()
    last_usb_check = time.ticks_ms()
    last_led_update = time.ticks_ms()

    # Set up transport: CDC (existing) or HID (new). For now, default to
    # CDC so behavior is unchanged until a HID-capable build is ready.
    hid_transport = None
    event_sink = None
    if USE_HID_TRANSPORT:
        from hid_transport import HIDTransport
        hid_transport = HIDTransport(command_router)
        if hid_transport is not None:
            event_sink = hid_transport.send_message_from_app
    else:
        usb_handler.set_command_callback(handle_usb_command)

    # Provide structured event sink to handlers (no-op if None)
    button_handler.set_event_sink(event_sink)
    encoder_handler.set_event_sink(event_sink)

    # Main loop
    while True:
        current_time = time.ticks_ms()

        # Handle reset request (non-blocking)
        if reset_requested:
            time.sleep_ms(100)  # Brief delay for cleanup
            machine.reset()

        # Process USB/HID communication (every 5ms)
        if time.ticks_diff(current_time, last_usb_check) >= USB_CHECK_INTERVAL:
            last_usb_check = current_time
            if USE_HID_TRANSPORT and hid_transport is not None:
                hid_transport.poll()
            else:
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
