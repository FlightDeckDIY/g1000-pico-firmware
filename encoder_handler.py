# Enhanced Encoder Handler Module with Interrupt-Driven Processing

import time
from machine import Pin
from config import *
from mode_manager import PFD_MODE, MFD_MODE

class EncoderHandler:
    def __init__(self, mode_manager=None, led_controller=None):
        self.mode_manager = mode_manager
        self.led_controller = led_controller
        # Circular buffer for encoder events (prevents data loss)
        self.encoder_buffer = []
        self.max_buffer_size = 200
        self.buffer_overflow_count = 0
        # Encoder state tracking with enhanced quadrature decoding
        self.encoder_states = {}
        # Complete quadrature state transition table
        self.quadrature_table = {
            # Clockwise sequence: 00 -> 01 -> 11 -> 10 -> 00
            (0, 0, 1, 0): (1, True, 1),   # CW step 1
            (1, 0, 1, 1): (1, True, 2),   # CW step 2
            (1, 1, 0, 1): (1, True, 3),   # CW step 3
            (0, 1, 0, 0): (1, True, 4),   # CW step 4 (complete detent)
            # Counter-clockwise sequence: 00 -> 10 -> 11 -> 01 -> 00
            (0, 0, 0, 1): (-1, True, 1),  # CCW step 1
            (0, 1, 1, 1): (-1, True, 2),  # CCW step 2
            (1, 1, 1, 0): (-1, True, 3),  # CCW step 3
            (1, 0, 0, 0): (-1, True, 4),  # CCW step 4 (complete detent)
            # No change states
            (0, 0, 0, 0): (0, True, 0),  # Rest position
            (0, 1, 0, 1): (0, True, 0),  # Stable intermediate
            (1, 1, 1, 1): (0, True, 0),  # Stable intermediate
            (1, 0, 1, 0): (0, True, 0),  # Stable intermediate
        }
        # Initialize encoder states for direct MCU encoders
        for encoder in ENCODERS:
            name, pin_a, pin_b, detent_type = encoder
            self.encoder_states[name] = {
                'last_state': (0, 0),
                'current_state': (0, 0),
                'last_detent_time': 0,
                'last_direction': 0,
                'last_speed': 1,
                'sequence_step': 0,        # Track position in quadrature sequence
                'expected_direction': 0,   # Expected direction based on sequence
                'invalid_transitions': 0,  # Count invalid state changes
                'total_detents': 0,       # Total detents processed
                'missed_transitions': 0,   # Estimated missed transitions
                'last_interrupt_time': 0, # Time of last interrupt
                'pin_a_pin': None,        # Pin object for interrupt setup
                'pin_b_pin': None,        # Pin object for interrupt setup
                'detent_type': detent_type # Single or dual detent encoder
            }

        # Circular buffer for encoder events (prevents data loss)
        self.encoder_buffer = []
        self.max_buffer_size = 200
        self.buffer_overflow_count = 0
        
        # Encoder state tracking with enhanced quadrature decoding
        self.encoder_states = {}
        
        # Complete quadrature state transition table
        # (prev_a, prev_b, curr_a, curr_b): (direction, valid, step)
        self.quadrature_table = {
            # Clockwise sequence: 00 -> 01 -> 11 -> 10 -> 00
            (0, 0, 1, 0): (1, True, 1),   # CW step 1
            (1, 0, 1, 1): (1, True, 2),   # CW step 2
            (1, 1, 0, 1): (1, True, 3),   # CW step 3
            (0, 1, 0, 0): (1, True, 4),   # CW step 4 (complete detent)
            
            # Counter-clockwise sequence: 00 -> 10 -> 11 -> 01 -> 00
            (0, 0, 0, 1): (-1, True, 1),  # CCW step 1
            (0, 1, 1, 1): (-1, True, 2),  # CCW step 2
            (1, 1, 1, 0): (-1, True, 3),  # CCW step 3
            (1, 0, 0, 0): (-1, True, 4),  # CCW step 4 (complete detent)
            
            # No change states
            (0, 0, 0, 0): (0, True, 0),  # Rest position
            (0, 1, 0, 1): (0, True, 0),  # Stable intermediate
            (1, 1, 1, 1): (0, True, 0),  # Stable intermediate
            (1, 0, 1, 0): (0, True, 0),  # Stable intermediate
        }
        
        # Initialize encoder states for direct MCU encoders
        for encoder in ENCODERS:
            name, pin_a, pin_b, detent_type = encoder
            self.encoder_states[name] = {
                'last_state': (0, 0),
                'current_state': (0, 0),
                'last_detent_time': 0,
                'last_direction': 0,
                'last_speed': 1,
                'sequence_step': 0,        # Track position in quadrature sequence
                'expected_direction': 0,   # Expected direction based on sequence
                'invalid_transitions': 0,  # Count invalid state changes
                'total_detents': 0,       # Total detents processed
                'missed_transitions': 0,   # Estimated missed transitions
                'last_interrupt_time': 0, # Time of last interrupt
                'pin_a_pin': None,        # Pin object for interrupt setup
                'pin_b_pin': None,        # Pin object for interrupt setup
                'detent_type': detent_type # Single or dual detent encoder
            }

    def initialize_mcp_encoders(self, encoder_pairs):
        """Initialize encoder states for MCP23017 encoders."""
        for encoder_pair in encoder_pairs:
            self.encoder_states[encoder_pair['name']] = {
                'last_state': (0, 0),
                'current_state': (0, 0),
                'last_detent_time': 0,
                'last_direction': 0,
                'last_speed': 1,
                'sequence_step': 0,
                'expected_direction': 0,
                'invalid_transitions': 0,
                'total_detents': 0,
                'missed_transitions': 0,
                'last_interrupt_time': 0,
                'device': encoder_pair['device'],
                'pin_a': encoder_pair['pin_a'],
                'pin_b': encoder_pair['pin_b'],
                'is_mcp': True,
                'detent_type': encoder_pair.get('detent_type', 'dual')  # Add detent type support
            }
    
    def setup_interrupts(self, encoder_pins):
        """Setup GPIO interrupts for direct MCU encoders."""
        for encoder in ENCODERS:
            encoder_name = encoder[0]
            state = self.encoder_states[encoder_name]
            pins = encoder_pins[encoder_name]
            
            # Store pin references
            state['pin_a_pin'] = pins['pin_a']
            state['pin_b_pin'] = pins['pin_b']
            
            # Create interrupt handlers with proper closure
            def make_handler(name):
                return lambda p: self._encoder_interrupt(name, p)
            
            # Setup interrupts on both pins
            pins['pin_a'].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, 
                            handler=make_handler(encoder_name))
            pins['pin_b'].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, 
                            handler=make_handler(encoder_name))
    
    def _encoder_interrupt(self, encoder_name, pin):
        """Fast interrupt handler - just buffer the event."""
        try:
            # Get current time with microsecond precision
            current_time = time.ticks_us()
            
            # Read both pins immediately
            state = self.encoder_states[encoder_name]
            pin_a = state['pin_a_pin'].value()
            pin_b = state['pin_b_pin'].value()
            
            # Add to circular buffer if space available
            if len(self.encoder_buffer) < self.max_buffer_size:
                self.encoder_buffer.append({
                    'encoder': encoder_name,
                    'pin_a': pin_a,
                    'pin_b': pin_b,
                    'time': current_time,
                    'source': 'direct'
                })
            else:
                # Buffer overflow - increment counter
                self.buffer_overflow_count += 1
                
        except Exception:
            # Interrupt handlers should never raise exceptions
            pass

    def process_encoder_change(self, encoder_name, current_a, current_b, current_time):
        """Enhanced encoder processing with complete quadrature validation."""
        if encoder_name not in self.encoder_states:
            return False, 0, 0
        
        state = self.encoder_states[encoder_name]
        prev_a, prev_b = state['last_state']
        
        # Only process if state actually changed
        if current_a == prev_a and current_b == prev_b:
            return False, 0, 0
        
        # Update current state
        state['current_state'] = (current_a, current_b)
        state['last_interrupt_time'] = current_time
        
        # Look up transition in quadrature table
        transition_key = (prev_a, prev_b, current_a, current_b)
        
        if transition_key in self.quadrature_table:
            direction, is_valid, step = self.quadrature_table[transition_key]
            
            # Only allow speed > 1 for HDG and CRS/BARO encoders
            speed_sensitive_encoders = [
                'HDG_BUG', 'CRS_BARO_MINOR', 'CRS_BARO_MAJOR'
            ]
            
            if is_valid and direction != 0:  # Valid transition with movement
                # Update sequence tracking
                if step == 1:  # Starting new sequence
                    state['expected_direction'] = direction
                    state['sequence_step'] = 1
                elif state['expected_direction'] == direction and step == state['sequence_step'] + 1:
                    # Valid continuation of sequence
                    state['sequence_step'] = step
                elif state['expected_direction'] != direction:
                    # Direction change detected - immediately reset and start new sequence
                    state['expected_direction'] = direction
                    state['sequence_step'] = step  # Use current step, not reset to 1
                    # For immediate direction change detection, treat step 1 as a mini-detent
                    if step == 1:
                        # Immediate direction change detection - generate detent event
                        time_diff_us = time.ticks_diff(current_time, state['last_detent_time'])
                        # Only allow speed > 1 for HDG and CRS/BARO encoders
                        if encoder_name in speed_sensitive_encoders:
                            speed = self._calculate_speed(time_diff_us)
                        else:
                            speed = 1
                        
                        state['last_direction'] = direction
                        state['last_speed'] = speed
                        state['last_detent_time'] = current_time
                        state['total_detents'] += 1
                        
                        direction_str = "CW" if direction > 0 else "CCW"
                        mode_str = 'PFD' if self.mode_manager and self.mode_manager.mode == PFD_MODE else 'MFD'
                        print(f"EVENT::ROTARY:{mode_str}:{encoder_name}:{direction_str}:{speed}")
                        self._handle_encoder_action(encoder_name, direction, speed)
                        
                        state['last_state'] = (current_a, current_b)
                        return True, direction, speed
                else:
                    # Invalid sequence step
                    state['invalid_transitions'] += 1
                
                # Check for completed detent based on encoder type
                detent_type = state.get('detent_type', 'dual')  # Default to dual for MCP encoders
                
                detent_detected = False
                if detent_type == "single":
                    # Single detent encoders: only count step 4 (return to 00)
                    detent_detected = (step == 4 and state['sequence_step'] == 4)
                else:  # dual
                    # Dual detent encoders: count both step 2 (reach 11) and step 4 (return to 00)
                    detent_detected = ((step == 4 and state['sequence_step'] == 4) or 
                                     (step == 2 and state['sequence_step'] == 2))
                
                
                if detent_detected:
                    # Calculate speed based on time between detents
                    time_diff_us = time.ticks_diff(current_time, state['last_detent_time'])
                    # Only allow speed > 1 for HDG and CRS/BARO encoders
                    if encoder_name in speed_sensitive_encoders:
                        speed = self._calculate_speed(time_diff_us)
                    else:
                        speed = 1
                    
                    # Update state
                    state['last_direction'] = direction
                    state['last_speed'] = speed
                    state['last_detent_time'] = current_time
                    state['total_detents'] += 1
                    
                    # Reset sequence for next detent (but don't reset to 0 if we're at step 2)
                    if step == 4:
                        state['sequence_step'] = 0  # Full cycle complete
                    # If step == 2, keep sequence_step as is to continue to step 3,4
                    
                    # Print encoder info with standardized format
                    direction_str = "CW" if direction > 0 else "CCW"
                    mode_str = 'PFD' if hasattr(self, 'mode_manager') and self.mode_manager and self.mode_manager.mode == PFD_MODE else 'MFD'
                    print(f"EVENT::ROTARY:{mode_str}:{encoder_name}:{direction_str}:{speed}")
                    self._handle_encoder_action(encoder_name, direction, speed)
                    
                    # Update last state after successful detent
                    state['last_state'] = (current_a, current_b)
                    return True, direction, speed
        else:
            # Invalid transition - log it
            state['invalid_transitions'] += 1
            # print(f" encoder transition {encoder_name}: {prev_a}{prev_b} -> {current_a}{current_b}")
        
        # Update last state
        state['last_state'] = (current_a, current_b)
        return False, 0, 0
    
    def _calculate_speed(self, time_diff_us):
        """Calculate encoder speed based on time between detents."""
        if time_diff_us <= 0:
            return 1
        
        time_diff_ms = time_diff_us / 1000
        
        if time_diff_ms < 15:      # < 15ms = very fast
            return 5
        elif time_diff_ms < 30:    # < 30ms = fast
            return 4
        elif time_diff_ms < 60:    # < 60ms = medium-fast
            return 3
        elif time_diff_ms < 90:   # < 120ms = medium
            return 2
        else:
            return 1               # >= 120ms = slow

    def _handle_encoder_action(self, encoder_name, direction, speed):
        """Trigger any side effects tied to encoder detents."""
        if encoder_name == "NAV_VOL" and self.led_controller:
            delta = NAV_VOL_BRIGHTNESS_STEP * direction
            new_brightness = self.led_controller.adjust_brightness(delta)
            direction_str = "UP" if direction > 0 else "DOWN"
            print(f"EVENT::BACKLIGHT:{encoder_name}:{direction_str}:{new_brightness}")

    def process_buffered_events(self):
        """Process all buffered encoder events from interrupts."""
        events_processed = 0
        
        # Process all events in buffer
        while self.encoder_buffer:
            event = self.encoder_buffer.pop(0)
            events_processed += 1
            
            # Process the encoder change
            detent_completed, direction, speed = self.process_encoder_change(
                event['encoder'], 
                event['pin_a'], 
                event['pin_b'], 
                event['time']
            )
            
            # Handle completed detent if needed
            if detent_completed:
                # Could add additional processing here
                pass
        
        return events_processed
    
    def process_direct_encoders_polling(self, current_time, encoder_pins):
        """Fallback polling method for direct encoders (used if interrupts fail)."""
        for encoder in ENCODERS:
            encoder_name = encoder[0]
            state = self.encoder_states[encoder_name]
            
            # Use pre-initialized pins for faster access
            pins = encoder_pins[encoder_name]
            current_a = pins['pin_a'].value()
            current_b = pins['pin_b'].value()
            
            # Check if state changed
            if (current_a != state['current_state'][0] or 
                current_b != state['current_state'][1]):
                
                # Process the state change directly
                detent_completed, direction, speed = self.process_encoder_change(
                    encoder_name, current_a, current_b, time.ticks_us()
                )

    def process_mcp_pin_change(self, device_name, pin_name, port, bit, pin_value, current_time, encoder_pairs, port_values):
        """Process a pin change that might be part of an MCP23017 encoder pair."""
        for encoder_pair in encoder_pairs:
            if encoder_pair['device'] != device_name:
                continue
                
            encoder_name = encoder_pair['name']
            pin_a_info = encoder_pair['pin_a']
            pin_b_info = encoder_pair['pin_b']
            
            # Check if this pin change is for pin A or pin B of this encoder
            is_pin_a = (pin_a_info['port'] == port and pin_a_info['bit'] == bit and pin_a_info['name'] == pin_name)
            is_pin_b = (pin_b_info['port'] == port and pin_b_info['bit'] == bit and pin_b_info['name'] == pin_name)
            
            if is_pin_a or is_pin_b:
                # Get current state of both pins
                current_port_a = port_values[device_name]['current'][pin_a_info['port']]
                current_port_b = port_values[device_name]['current'][pin_b_info['port']]
                
                # Remove the inversion of pin values to fix direction
                pin_a_val = (current_port_a >> pin_a_info['bit']) & 1
                pin_b_val = (current_port_b >> pin_b_info['bit']) & 1
                
                # Add to buffer for processing
                if len(self.encoder_buffer) < self.max_buffer_size:
                    self.encoder_buffer.append({
                        'encoder': encoder_name,
                        'pin_a': pin_a_val,
                        'pin_b': pin_b_val,
                        'time': current_time * 1000,  # Convert ms to us for consistency
                        'source': 'mcp'
                    })
                else:
                    self.buffer_overflow_count += 1
                
                break
    
    def get_encoder_stats(self):
        """Get diagnostic information about encoder performance."""
        stats = {
            'buffer_size': len(self.encoder_buffer),
            'buffer_overflows': self.buffer_overflow_count,
            'encoders': {}
        }
        
        for name, state in self.encoder_states.items():
            stats['encoders'][name] = {
                'total_detents': state.get('total_detents', 0),
                'invalid_transitions': state.get('invalid_transitions', 0),
                'last_speed': state.get('last_speed', 0),
                'last_direction': state.get('last_direction', 0)
            }
        
        return stats
    
    def reset_stats(self):
        """Reset diagnostic counters."""
        self.buffer_overflow_count = 0
        for state in self.encoder_states.values():
            state['invalid_transitions'] = 0
            state['total_detents'] = 0
