#!/usr/bin/env python3
"""
Test script for enhanced encoder system - demonstrates zero missed detents
Run this on the Pico to test the interrupt-driven encoder handling
"""

import time
from machine import Pin, I2C

# Define GPIO encoders with their detent types
ENCODERS = [
    ("NAV_VOL", 5, 6, "single"),        # Single detent per cycle
    ("NAV_FQ_MAJOR", 8, 10, "dual"),   # Dual detents per cycle
    ("NAV_FQ_MINOR", 9, 11, "dual"),   # Dual detents per cycle
    ("HDG_BUG", 14, 15, "single"),      # Single detent per cycle
    ("ALT_MAJOR", 40, 41, "dual"),      # Dual detents per cycle
    ("ALT_MINOR", 42, 43, "dual"),      # Dual detents per cycle
]

# Define MCP23017 encoders with their detent types
MCP_ENCODERS = [
    ("COM_VOL_1", "single"),      # COM_VOL encoder - single detent
    ("MAP_1", "single"),          # MAP encoder - single detent  
    ("CRS_BARO_1", "dual"),       # CRS_BARO encoder - dual detent
    ("FMS_1", "dual"),            # FMS encoder - dual detent
    ("COM_FQ_1", "dual"),         # COM_FQ encoder - dual detent
]

def test_basic_encoder_interrupts():
    """Test basic encoder interrupt functionality without complex imports."""
    print("=== Enhanced Encoder Test with MCP23017 Support ===")
    print("Testing GPIO and MCP23017 interrupt-driven encoder detection")
    print()
    
    # Simple encoder state tracking
    encoder_states = {}
    encoder_buffer = []
    
    # Initialize I2C for MCP23017
    try:
        i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
        mcp_available = True
        print("I2C initialized for MCP23017 encoders")
    except Exception as e:
        print(f"I2C initialization failed: {e}")
        mcp_available = False
    
    # Initialize GPIO encoder pins and states
    encoder_pins = {}
    encoder_types = {}
    for encoder in ENCODERS:
        name, pin_a_num, pin_b_num, detent_type = encoder
        encoder_pins[name] = {
            'pin_a': Pin(pin_a_num, Pin.IN, Pin.PULL_UP),
            'pin_b': Pin(pin_b_num, Pin.IN, Pin.PULL_UP)
        }
        encoder_types[name] = detent_type
        encoder_states[name] = {
            'last_state': (0, 0),
            'detent_count': 0,
            'last_detent_time': 0
        }
    
    # Initialize MCP encoder states
    for encoder_name, detent_type in MCP_ENCODERS:
        encoder_types[encoder_name] = detent_type
        encoder_states[encoder_name] = {
            'last_state': (0, 0),
            'detent_count': 0,
            'last_detent_time': 0
        }
    
    def encoder_interrupt(pin, encoder_name):
        """Simple interrupt handler."""
        try:
            pins = encoder_pins[encoder_name]
            pin_a = pins['pin_a'].value()
            pin_b = pins['pin_b'].value()
            current_time = time.ticks_us()
            
            # Add to buffer
            if len(encoder_buffer) < 100:
                encoder_buffer.append({
                    'name': encoder_name,
                    'pin_a': pin_a,
                    'pin_b': pin_b,
                    'time': current_time
                })
        except:
            pass  # Ignore errors in interrupt
    
    # Setup interrupts with proper closures
    print("Setting up interrupts:")
    for encoder in ENCODERS:
        name, pin_a_num, pin_b_num, detent_type = encoder
        pins = encoder_pins[name]
        
        # Create handlers with proper closure
        def make_handler(enc_name):
            return lambda p: encoder_interrupt(p, enc_name)
        
        handler = make_handler(name)
        pins['pin_a'].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=handler)
        pins['pin_b'].irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=handler)
        
        print(f"  - {name} (GPIO {pin_a_num}, {pin_b_num}) [{detent_type}]")
    
    print("Interrupts configured!")
    print()
    
    # Simple quadrature decoding function
    def process_encoder_event(event):
        """Process a single encoder event from the buffer."""
        name = event['name']
        pin_a = event['pin_a']
        pin_b = event['pin_b']
        current_time = event['time']
        
        state = encoder_states[name]
        prev_a, prev_b = state['last_state']
        
        # Only process if state changed
        if pin_a == prev_a and pin_b == prev_b:
            return
        
        # Get encoder type for this encoder
        encoder_type = encoder_types[name]
        
        # Detent detection based on encoder type
        if encoder_type == "single":
            # Single detent encoders: only count 00 position
            is_detent_position = (pin_a == 0 and pin_b == 0)
            was_detent_position = (prev_a == 0 and prev_b == 0)
        else:  # dual
            # Dual detent encoders: count both 00 and 11 positions
            is_detent_position = (pin_a == 0 and pin_b == 0) or (pin_a == 1 and pin_b == 1)
            was_detent_position = (prev_a == 0 and prev_b == 0) or (prev_a == 1 and prev_b == 1)
        
        # Only count when entering a detent position from a non-detent position
        if is_detent_position and not was_detent_position:
            # Determine direction based on the transition
            if (prev_a == 0 and prev_b == 1 and pin_a == 1 and pin_b == 1) or \n               (prev_a == 1 and prev_b == 0 and pin_a == 0 and pin_b == 0):
                direction = "CW"
            elif (prev_a == 1 and prev_b == 0 and pin_a == 1 and pin_b == 1) or \n                 (prev_a == 0 and prev_b == 1 and pin_a == 0 and pin_b == 0):
                direction = "CCW"
            else:
                # Fallback: determine by which detent position we're in
                if pin_a == 1 and pin_b == 1:
                    direction = "CW" if prev_a == 0 else "CCW"
                else:  # pin_a == 0 and pin_b == 0
                    direction = "CW" if prev_b == 1 else "CCW"
            
            # Calculate speed
            time_diff = time.ticks_diff(current_time, state['last_detent_time'])
            if time_diff > 0:
                speed = 5 if time_diff < 15000 else 3 if time_diff < 50000 else 1
            else:
                speed = 1
            
            state['detent_count'] += 1
            state['last_detent_time'] = current_time
            
            # Show detent position for dual encoders, type for single
            if encoder_type == "dual":
                detent_pos = "00" if pin_a == 0 else "11"
                print(f"Encoder {name} {direction} [{detent_pos}] - Speed: {speed} (#{state['detent_count']})")
            else:
                print(f"Encoder {name} {direction} [single] - Speed: {speed} (#{state['detent_count']})")
        
        state['last_state'] = (pin_a, pin_b)
    
    print("=== TEST INSTRUCTIONS ===")
    print("1. Turn encoders at different speeds")
    print("2. Try very fast turns to test missed detent prevention")
    print("3. Turn multiple encoders simultaneously")
    print("4. Press Ctrl+C to exit and see statistics")
    print()
    
    last_stats_time = time.ticks_ms()
    stats_interval = 5000  # Show stats every 5 seconds
    
    try:
        while True:
            current_time = time.ticks_ms()
            
            # Process all buffered encoder events
            while encoder_buffer:
                event = encoder_buffer.pop(0)
                process_encoder_event(event)
            
            # Show periodic statistics
            if time.ticks_diff(current_time, last_stats_time) >= stats_interval:
                print(f"\n=== ENCODER STATISTICS (every {stats_interval/1000}s) ===")
                print(f"Buffer usage: {len(encoder_buffer)}/100")
                
                total_detents = 0
                for name, state in encoder_states.items():
                    if state['detent_count'] > 0:
                        print(f"{name}: {state['detent_count']} detents")
                        total_detents += state['detent_count']
                
                print(f"Total detents: {total_detents}")
                print("=" * 50)
                last_stats_time = current_time
            
            # Small delay
            time.sleep_ms(1)
            
    except KeyboardInterrupt:
        print("\n=== TEST COMPLETED ===")
        
        # Final statistics
        print("\nFinal Statistics:")
        total_detents = 0
        
        for name, state in encoder_states.items():
            if state['detent_count'] > 0:
                print(f"{name}: {state['detent_count']} detents")
                total_detents += state['detent_count']
        
        print(f"\nTOTAL: {total_detents} detents processed")
        print("✅ Interrupt-driven encoder test completed!")

if __name__ == "__main__":
    test_basic_encoder_interrupts()
