"""
USB Communication Handler for G1P Application
Handles non-blocking serial communication with the host computer
"""
import sys
import select
import time
import machine
from binascii import hexlify

class USBHandler:
    def __init__(self):
        self.input_buffer = ''
        self.command_queue = []
        self.last_activity = time.ticks_ms()
        self.connected = False
        self.command_callback = None
        
    def set_command_callback(self, callback):
        """Set the callback function for processing commands"""
        self.command_callback = callback
        
    def check_connection(self):
        """Check if USB is connected by checking for data availability"""
        try:
            # Try to read a character to check connection
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                self.last_activity = time.ticks_ms()
                if not self.connected:
                    self.connected = True
                    return True, True  # New connection
                return True, False  # Still connected
                
            # Timeout after 1 second of inactivity
            if self.connected and time.ticks_diff(time.ticks_ms(), self.last_activity) > 1000:
                self.connected = False
                return False, True  # Disconnected
                
            return self.connected, False  # No change
            
        except Exception as e:
            print(f"USB_ERR:{e}")
            return False, False
            
    def read_commands(self):
        """Read available data and buffer complete commands"""
        try:
            while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                if not char:
                    break
                    
                self.last_activity = time.ticks_ms()
                
                if char in '\r\n':
                    if self.input_buffer:
                        self.command_queue.append(self.input_buffer)
                        self.input_buffer = ''
                else:
                    self.input_buffer += char
                    
        except Exception as e:
            print(f"USB_READ_ERR:{e}")
            self.input_buffer = ''
            
    def process_commands(self):
        """Process any buffered commands using the callback"""
        if not self.command_queue or not self.command_callback:
            return self.connected
            
        line = self.command_queue.pop(0).strip()
        if not line:
            return self.connected
            
        try:
            # Let the callback handle the command
            self.command_callback(line)
            
        except Exception as e:
            print(f"CMD_ERROR:{e}")
            
        return self.connected

# Global instance
usb_handler = USBHandler()

def handle_serial_commands():
    """Main entry point for handling USB communication"""
    try:
        # Check connection status
        connected, _ = usb_handler.check_connection()
        
        # Read any available data
        usb_handler.read_commands()
        
        # Process any complete commands
        return usb_handler.process_commands()
    except Exception as e:
        print(f"USB_HANDLER_ERROR:{e}")
        return False
