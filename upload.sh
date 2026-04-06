#!/bin/bash

DEVICE="/dev/tty.usbmodem12101"
FILES=(
    button_handler.py
    config.py
    encoder_handler.py
    led_controller.py
    main.py
    mcp23017_handler.py
    mode_manager.py
    usb_comm.py
)

if [ ! -e "$DEVICE" ]; then
    echo "Error: Pico not found at $DEVICE"
    exit 1
fi

echo "Uploading to $DEVICE..."
mpremote connect "$DEVICE" cp "${FILES[@]}" :
echo "Done."
