# Button Handler Module

import time
from config import *
from mode_manager import PFD_MODE, MFD_MODE

class ButtonHandler:
    def __init__(self, mode_manager=None, button_event_callback=None):
        # Button state tracking for long press detection
        self.mode_manager = mode_manager
        self.button_event_callback = button_event_callback
        self.button_states = {}
        
        # Track last repeat time for map direction buttons
        self.map_direction_repeat_times = {
            'MAP_UP': 0,
            'MAP_DOWN': 0,
            'MAP_LEFT': 0,
            'MAP_RIGHT': 0
        }
        
        # Initialize button states for direct MCU buttons
        for button in BUTTONS:
            self.button_states[button[0]] = {
                'is_pressed': False,
                'press_time': 0,
                'hold_reported': False,
                'hold_threshold': BUTTON_HOLD_THRESHOLD_MS,
                'source': 'direct'
            }
        
        # Initialize button states for MCP23017 buttons
        for dev_name, mappings in MCP23017_MAPS.items():
            for port, pins in mappings.items():
                for i, pin_name in enumerate(pins):
                    if pin_name not in self.button_states:
                        self.button_states[pin_name] = {
                            'is_pressed': False,
                            'press_time': 0,
                            'hold_reported': False,
                            'hold_threshold': BUTTON_HOLD_THRESHOLD_MS,
                            'source': 'mcp',
                            'device': dev_name,
                            'port': port,
                            'bit': i
                        }
        
        # MAP button filtering state
        self.map_push_state = {
            'pending_press': False,
            'pending_release': False,
            'press_time': 0,
            'release_time': 0,
            'timeout_ms': MAP_PUSH_TIMEOUT_MS,
            'direction_active': False,
            'last_direction_time': 0
        }

    def _notify_button_event(self, button_name, action):
        """Notify the main loop about local button side effects."""
        if self.button_event_callback:
            self.button_event_callback(button_name, action)

    def is_map_direction_button(self, pin_name):
        """Check if a pin is a MAP direction button."""
        return pin_name in ['MAP_RIGHT', 'MAP_UP', 'MAP_DOWN', 'MAP_LEFT']

    def handle_map_button_event(self, pin_name, is_pressed, current_time):
        """Handle MAP button events with filtering logic."""
        if pin_name == "MAP_PUSH":
            # Check if any direction button was pressed recently
            recent_direction = time.ticks_diff(current_time, self.map_push_state['last_direction_time']) < MAP_DIRECTION_SUPPRESSION_WINDOW_MS
            
            if is_pressed:
                # MAP_PUSH pressed - check if direction is active or was recent
                if self.map_push_state['direction_active'] or recent_direction:
                    return False  # Suppress
                else:
                    # No direction active, start pending state
                    self.map_push_state['pending_press'] = True
                    self.map_push_state['press_time'] = current_time
                    return False  # Suppress printing, wait for timeout
            else:
                # MAP_PUSH released - check if direction is active or was recent
                if self.map_push_state['direction_active'] or recent_direction:
                    return False  # Suppress
                else:
                    # No direction active and no recent direction
                    self.map_push_state['pending_release'] = True
                    self.map_push_state['release_time'] = current_time
                    return False  # Suppress printing, wait for timeout
        
        elif self.is_map_direction_button(pin_name):
            if is_pressed:
                # Direction button pressed
                self.map_push_state['direction_active'] = True
                self.map_push_state['last_direction_time'] = current_time
                # Cancel any pending MAP_PUSH events
                self.map_push_state['pending_press'] = False
                self.map_push_state['pending_release'] = False
                return True  # Allow normal processing
            else:
                # Direction button released
                self.map_push_state['direction_active'] = False
                self.map_push_state['last_direction_time'] = current_time  # Extend suppression window
                # Cancel any pending MAP_PUSH release
                self.map_push_state['pending_release'] = False
                return True  # Allow normal processing
        
        return True  # Allow normal processing for other buttons

    def check_map_push_timeout(self, current_time):
        """Check if MAP_PUSH timeout has expired and process pending events."""
        # Check for pending press timeout
        if (self.map_push_state['pending_press'] and 
            time.ticks_diff(current_time, self.map_push_state['press_time']) >= self.map_push_state['timeout_ms']):
            # Timeout expired, this is a genuine MAP_PUSH press
            mode_str = 'PFD' if self.mode_manager and self.mode_manager.mode == PFD_MODE else 'MFD'
            print(f"EVENT::BUTTON:{mode_str}:MAP_PUSH:PRESS")
            self._notify_button_event("MAP_PUSH", "PRESS")
            self.map_push_state['pending_press'] = False
        
        # Check for pending release timeout
        if (self.map_push_state['pending_release'] and 
            time.ticks_diff(current_time, self.map_push_state['release_time']) >= self.map_push_state['timeout_ms']):
            # Timeout expired, this is a genuine MAP_PUSH release
            mode_str = 'PFD' if self.mode_manager and self.mode_manager.mode == PFD_MODE else 'MFD'
            print(f"EVENT::BUTTON:{mode_str}:MAP_PUSH:RELEASE")
            self._notify_button_event("MAP_PUSH", "RELEASE")
            self.map_push_state['pending_release'] = False

    def process_direct_buttons(self, current_time, button_pins):
        """Process direct MCU button inputs."""
        for button in BUTTONS:
            button_name = button[0]
            button_state = self.button_states[button_name]
            
            # Use pre-initialized pin for faster access
            is_pressed = not button_pins[button_name].value()  # True if pressed (pulled low)
            
            # Check for state change
            if is_pressed != button_state['is_pressed']:
                if is_pressed:  # Button was just pressed
                    button_state['press_time'] = current_time
                    mode_str = 'PFD' if (self.mode_manager and self.mode_manager.mode == PFD_MODE) else 'MFD'
                    print(f"EVENT::BUTTON:{mode_str}:{button_name}:PRESS")
                    self._notify_button_event(button_name, "PRESS")
                else:  # Button was just released
                    button_state['hold_reported'] = False
                    mode_str = 'PFD' if self.mode_manager and self.mode_manager.mode == PFD_MODE else 'MFD'
                    print(f"EVENT::BUTTON:{mode_str}:{button_name}:RELEASE")
                    self._notify_button_event(button_name, "RELEASE")
                # Update the stored state
                button_state['is_pressed'] = is_pressed
            # Check for hold (only if currently pressed and hold not yet reported)
            elif is_pressed and not button_state['hold_reported']:
                if time.ticks_diff(current_time, button_state['press_time']) >= button_state['hold_threshold']:
                    mode_str = 'PFD' if (self.mode_manager and self.mode_manager.mode == PFD_MODE) else 'MFD'
                    print(f"EVENT::BUTTON:{mode_str}:{button_name}:HOLD")
                    print(f"EVENT::BUTTON:{mode_str}:{button_name}:HOLD")
                    self._notify_button_event(button_name, "HOLD")
                    button_state['hold_reported'] = True

    def process_mcp_buttons(self, current_time):
        """Process MCP23017 button inputs with repeat support for map direction buttons."""
        for button_name, button_state in self.button_states.items():
            if button_state['source'] != 'mcp' or not button_state['is_pressed']:
                continue
                
            # Check for hold (only if currently pressed and hold not yet reported)
            if not button_state['hold_reported']:
                if time.ticks_diff(current_time, button_state['press_time']) >= button_state['hold_threshold']:
                    button_state['hold_reported'] = True
                    mode_str = 'PFD' if (self.mode_manager and self.mode_manager.mode == PFD_MODE) else 'MFD'
                    print(f"EVENT::BUTTON:{mode_str}:{button_name}:HOLD")
                    self._notify_button_event(button_name, "HOLD")
            
            # Handle map direction button repeat with initial delay
            if button_name in ['MAP_UP', 'MAP_DOWN', 'MAP_LEFT', 'MAP_RIGHT']:
                held_time = time.ticks_diff(current_time, button_state['press_time'])
                if held_time >= MAP_REPEAT_DELAY_MS:
                    if time.ticks_diff(current_time, self.map_direction_repeat_times[button_name]) >= MAP_BUTTON_REPEAT_INTERVAL_MS:
                        mode_str = 'PFD' if (self.mode_manager and self.mode_manager.mode == PFD_MODE) else 'MFD'
                        print(f"EVENT::BUTTON:{mode_str}:{button_name}:PRESS")
                        self._notify_button_event(button_name, "PRESS")
                        self.map_direction_repeat_times[button_name] = current_time

    def handle_pin_change(self, pin_name, is_pressed, current_time, dev_name=None, port=None, bit=None, old_val=None, new_val=None):
        """Handle pin change events from MCP23017 devices."""
        # Check if this is a MAP button that needs filtering
        if pin_name == "MAP_PUSH" or self.is_map_direction_button(pin_name):
            if not self.handle_map_button_event(pin_name, is_pressed, current_time):
                return False  # Event was suppressed
        
        # Update button state for long press detection
        if pin_name in self.button_states:
            button_state = self.button_states[pin_name]
            if button_state['is_pressed'] != is_pressed:
                button_state.update({
                    'is_pressed': is_pressed,
                    'press_time': current_time if is_pressed else 0,
                    'hold_reported': not is_pressed
                })
                
                # Reset repeat timer for map direction buttons
                if pin_name in self.map_direction_repeat_times:
                    if is_pressed:
                        self.map_direction_repeat_times[pin_name] = current_time
                    else:
                        self.map_direction_repeat_times[pin_name] = 0
                
                # Only print press events here, release events are handled in process_mcp_buttons
                if is_pressed:
                    mode_str = 'PFD' if (self.mode_manager and self.mode_manager.mode == PFD_MODE) else 'MFD'
                    print(f"EVENT::BUTTON:{mode_str}:{pin_name}:PRESS")
                    self._notify_button_event(pin_name, "PRESS")
                else:
                    mode_str = 'PFD' if (self.mode_manager and self.mode_manager.mode == PFD_MODE) else 'MFD'
                    print(f"EVENT::BUTTON:{mode_str}:{pin_name}:RELEASE")
                    self._notify_button_event(pin_name, "RELEASE")
        
        return True  # Allow normal processing

    def process_long_press_detection(self, current_time, mode_manager):
        """Process long press detection for all buttons."""
        for button_name, state in self.button_states.items():
            if not state['is_pressed']:
                continue
                
            # Check for long press
            press_duration = time.ticks_diff(current_time, state['press_time'])
            if not state['hold_reported'] and press_duration >= state['hold_threshold']:
                state['hold_reported'] = True
                mode_str = 'PFD' if self.mode_manager and self.mode_manager.mode == PFD_MODE else 'MFD'
                print(f"EVENT::BUTTON:{mode_str}:{button_name}:LONG_PRESS")
                self._notify_button_event(button_name, "LONG_PRESS")
                # Handle specific long press actions
                self._handle_long_press(button_name, mode_manager)

    def _handle_long_press(self, button_name, mode_manager):
        """Handle long press actions for specific buttons."""
        if button_name == "NAV_SWAP":
            # Toggle between PFD and MFD modes
            if mode_manager.mode == PFD_MODE:
                mode_manager.change_mode(MFD_MODE)
            else:
                mode_manager.change_mode(PFD_MODE)
