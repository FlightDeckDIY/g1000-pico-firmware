# MCP23017 I2C Handler Module

import time
from machine import I2C, Pin
from config import *

class MCP23017Handler:
    def __init__(self, i2c):
        self.i2c = i2c
        self.connected_devices = []
        self.address_to_name = {addr: name for name, addr in MCP23017_ADDRESSES.items()}
        
        # Port value tracking
        self.port_values = {
            'BOTTOM': {
                'current': {'port_a': 0xFF, 'port_b': 0xFF},
                'previous': {'port_a': 0xFF, 'port_b': 0xFF}
            },
            'RIGHT_LOWER': {
                'current': {'port_a': 0xFF, 'port_b': 0xFF},
                'previous': {'port_a': 0xFF, 'port_b': 0xFF}
            },
            'RIGHT_UPPER': {
                'current': {'port_a': 0xFF, 'port_b': 0xFF},
                'previous': {'port_a': 0xFF, 'port_b': 0xFF}
            }
        }
        
        # Encoder pairs detection
        self.encoder_pairs = self._find_encoder_pairs()
        
    def read_register(self, register, device_address):
        """Read a single byte from the specified register of the MCP23017 device."""
        try:
            return self.i2c.readfrom_mem(device_address, register, 1)[0]
        except Exception as e:
            print(f"Error reading from register {register} at {hex(device_address)}: {e}")
            return 0xFF  # Return all high on error

    def write_to_register(self, register, value, device_address=None):
        """Write to MCP23017 register(s)."""
        if device_address is not None:
            self.i2c.writeto_mem(device_address, register, bytes([value]))
        else:
            for device in self.connected_devices:
                self.i2c.writeto_mem(device, register, bytes([value]))

    def setup_devices(self):
        """Initialize all MCP23017 devices."""
        try: 
            i2c_devices = self.i2c.scan()
            self.connected_devices = [addr for addr in MCP23017_ADDRESSES.values() if addr in i2c_devices]
            
            if not self.connected_devices:
                print("No MCP23017 devices found!")
                return False
                
            for addr in self.connected_devices:
                # Configure I/O direction (all inputs)
                self.write_to_register(IODIRA, 0xFF, addr)
                self.write_to_register(IODIRB, 0xFF, addr)
                
                # Configure input polarity (no inversion)
                self.write_to_register(IPOLA, 0x00, addr)
                self.write_to_register(IPOLB, 0x00, addr)
                
                # Configure pull-up resistors (all enabled)
                self.write_to_register(GPPUA, 0xFF, addr)
                self.write_to_register(GPPUB, 0xFF, addr)
                
                # Read initial port values
                port_a = self.read_register(GPIOA, addr)
                port_b = self.read_register(GPIOB, addr)
                
                # Initialize port values
                device_name = self.address_to_name[addr]
                self.port_values[device_name]['current']['port_a'] = port_a
                self.port_values[device_name]['current']['port_b'] = port_b
                self.port_values[device_name]['previous']['port_a'] = port_a
                self.port_values[device_name]['previous']['port_b'] = port_b
            
            return True
            
        except Exception as e:
            print(f"Failed to initialize I2C device: {e}")
            import sys
            sys.print_exception(e)
            return False

    def _find_encoder_pairs(self):
        """Find encoder pairs in MCP23017 devices based on _CW_ and _CCW_ naming."""
        encoder_pairs = []
        
        for device_name, mappings in MCP23017_MAPS.items():
            if device_name not in ['RIGHT_UPPER', 'RIGHT_LOWER']:
                continue
                
            # Collect all pins from both ports
            all_pins = []
            for port_name, pins in mappings.items():
                for bit, pin_name in enumerate(pins):
                    if '_CW' in pin_name or '_CCW' in pin_name:
                        all_pins.append({
                            'name': pin_name,
                            'device': device_name,
                            'port': port_name,
                            'bit': bit
                        })
            
            # Find pairs
            cw_pins = [p for p in all_pins if '_CW' in p['name']]
            ccw_pins = [p for p in all_pins if '_CCW' in p['name']]
            
            for cw_pin in cw_pins:
                # Extract base name and number
                cw_name = cw_pin['name']
                base_name = cw_name.replace('_CW', '_CCW')
                
                # Find matching CCW pin
                ccw_pin = next((p for p in ccw_pins if p['name'] == base_name), None)
                if ccw_pin:
                    # Create encoder name (remove _CW_ part and replace with _)
                    encoder_name = cw_name.replace('_CW', '') #if ('COM_VOL' in cw_name or 'MAP' in cw_name) else cw_name.replace('_CW', '_')
                    # Reverse the direction for specific encoders
                    if any(name in encoder_name for name in ['COM_FQ', 'CRS_BARO', 'FMS']):
                        pin_a = ccw_pin
                        pin_b = cw_pin
                    else:
                        pin_a = cw_pin
                        pin_b = ccw_pin
                        
                    encoder_pairs.append({
                        'name': encoder_name,
                        'device': device_name,
                        'pin_a': pin_a,
                        'pin_b': pin_b
                    })
        
        return encoder_pairs

    def is_encoder_pin(self, device_name, pin_name):
        """Check if a pin is part of an encoder pair to suppress individual pin messages."""
        for encoder_pair in self.encoder_pairs:
            if (encoder_pair['device'] == device_name and 
                (encoder_pair['pin_a']['name'] == pin_name or encoder_pair['pin_b']['name'] == pin_name)):
                return True
        return False

    def process_changes(self, current_time, button_handler, encoder_handler):
        """Process MCP23017 pin changes and delegate to appropriate handlers."""
        for addr in self.connected_devices:
            try:
                # Read current GPIO state
                port_a = self.i2c.readfrom_mem(addr, GPIOA, 1)[0]
                port_b = self.i2c.readfrom_mem(addr, GPIOB, 1)[0]
                
                # Get device name
                dev_name = self.address_to_name[addr]
                
                # Store previous values
                previous = self.port_values[dev_name]['current'].copy()
                
                # Update current values
                self.port_values[dev_name]['previous'] = previous
                self.port_values[dev_name]['current'] = {
                    'port_a': port_a,
                    'port_b': port_b
                }
                
                current = self.port_values[dev_name]['current']
                
                # Process Port A changes
                self._process_port_changes(dev_name, 'port_a', previous, current, 
                                         current_time, button_handler, encoder_handler)
                
                # Process Port B changes
                self._process_port_changes(dev_name, 'port_b', previous, current, 
                                         current_time, button_handler, encoder_handler)
                        
            except Exception as e:
                print(f"Error reading from device {hex(addr)}: {e}")

    def _process_port_changes(self, dev_name, port_name, previous, current, 
                            current_time, button_handler, encoder_handler):
        """Process changes for a specific port."""
        port_key = port_name
        changed = current[port_key] ^ previous[port_key]
        
        if changed:
            for bit in range(8):
                if changed & (1 << bit):
                    pin_name = MCP23017_MAPS[dev_name][port_name][bit] if bit < len(MCP23017_MAPS[dev_name][port_name]) else f"{port_name[-1].upper()}{bit}"
                    old_val = (previous[port_key] >> bit) & 1
                    new_val = (current[port_key] >> bit) & 1
                    is_pressed = new_val == 0
                    state = "pressed" if is_pressed else "released"
                    
                    # Handle pin change
                    if not self.is_encoder_pin(dev_name, pin_name):
                        # Handle button events (including MAP filtering)
                        button_handler.handle_pin_change(
                            pin_name, is_pressed, current_time, dev_name, port_name[-1].upper(), bit, old_val, new_val
                        )
                    
                    # Handle encoder events
                    encoder_handler.process_mcp_pin_change(
                        dev_name, pin_name, port_name, bit, new_val, current_time, self.encoder_pairs, self.port_values
                    )
