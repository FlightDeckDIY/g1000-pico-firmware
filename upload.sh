#!/bin/bash

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

usage() {
    echo "Usage: $0 [-h|--help] [usbmodem-number|device-path]"
    echo "Examples:"
    echo "  $0 12101"
    echo "  $0 /dev/tty.usbmodem12101"
    echo "  $0"
    echo "  $0 --help"
}

resolve_device() {
    local arg="$1"
    local matches
    local count

    if [ -n "$arg" ]; then
        if [[ "$arg" == /dev/* ]]; then
            echo "$arg"
        else
            echo "/dev/tty.usbmodem$arg"
        fi
        return 0
    fi

    matches=$(mpremote devs | awk '$1 ~ /\/dev\/(tty|cu)\.usbmodem/ { print $1 }')
    count=$(printf "%s\n" "$matches" | sed '/^$/d' | wc -l | tr -d ' ')

    if [ "$count" -eq 1 ]; then
        printf "%s\n" "$matches" | sed -n '1p'
        return 0
    fi

    if [ "$count" -eq 0 ]; then
        echo "Error: No usbmodem device found via mpremote devs." >&2
    else
        echo "Error: Multiple usbmodem devices found. Pass the usbmodem number or full device path." >&2
        printf "%s\n" "$matches" >&2
    fi
    return 1
}

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
    exit 0
fi

DEVICE=$(resolve_device "$1") || exit 1

if [ ! -e "$DEVICE" ]; then
    echo "Error: Pico not found at $DEVICE"
    exit 1
fi

echo "Uploading to $DEVICE..."
mpremote connect "$DEVICE" cp "${FILES[@]}" :
echo "Done."
