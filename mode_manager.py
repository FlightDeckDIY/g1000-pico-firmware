# Mode Manager for handling device modes and flash storage

import machine
import ujson
import os

# Flash storage configuration
FLASH_STORAGE_FILE = '/flash/mode.json'

# Mode constants
PFD_MODE = 0
MFD_MODE = 1


class ModeManager:
    def __init__(self):
        self.mode = self.load_mode_from_flash()
        self._mode_change_callbacks = []

    def register_mode_change_callback(self, callback):
        self._mode_change_callbacks.append(callback)

    def load_mode_from_flash(self):
        # Load mode from flash storage
        try:
            with open(FLASH_STORAGE_FILE, 'r') as file:
                return ujson.load(file).get('mode', PFD_MODE)
        except (OSError, ValueError):
            return PFD_MODE

    def save_mode_to_flash(self):
        # Save current mode to flash storage
        
        # Ensure the directory exists
        flash_dir = '/flash'
        try:
            os.mkdir(flash_dir)
        except OSError as e:
            # Directory already exists or other issue
            pass
            
        try:
            with open(FLASH_STORAGE_FILE, 'w') as file:
                ujson.dump({'mode': self.mode}, file)
        except OSError as e:
            print(f"Error saving mode: {e}")

    def change_mode(self, new_mode):
        # Change device mode
        if new_mode in (PFD_MODE, MFD_MODE):
            self.mode = new_mode
            self.save_mode_to_flash()
            print(f"Mode changed to: {'PFD' if self.mode == PFD_MODE else 'MFD'}")
            for cb in self._mode_change_callbacks:
                cb(self.mode)


def init():
    # Any initialization logic for mode management can be added here
    print("Mode manager initialized")
    pass
