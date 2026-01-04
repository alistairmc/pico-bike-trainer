from machine import Pin


class MotorSensor:
    """Motor sensor class for reading and counting motor RPM.
    
    This class handles hall sensor-based motor RPM readings (1 pulse per full 360 rotation).
    Uses GPIO pins with interrupt handlers to count rotations when pins go high.
    """
    
    def __init__(self, motor_count_gpio_pin=0, motor_stop_gpio_pin=1, screen_width=240, screen_height=240):
        """Initialize the motor sensor.
        
        Args:
            motor_count_gpio_pin: GPIO pin number for the motor hall sensor (default: 0).
            motor_stop_gpio_pin: GPIO pin number for the motor stop trigger (default: 1).
            screen_width: Width of the display screen in pixels (default: 240).
            screen_height: Height of the display screen in pixels (default: 240).
        """
        self.motor_count_gpio_pin = motor_count_gpio_pin
        self.motor_stop_gpio_pin = motor_stop_gpio_pin
        self.motor_rpm_pin = Pin(motor_count_gpio_pin, Pin.IN, Pin.PULL_UP)
        self.motor_pulse_count = 0  # Total pulse count for motor RPM
        self.motor_rotations_per_motor_crank = 1000  # 1000 motor rotations = 1 full motor crank rotation
        self.motor_count_since_last_motor_crank = 0  # Motor rotations since last motor crank pulse
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Set up interrupt handler for motor pulse counting
        # Use both rising and falling edges for better resolution on fast pulses
        # Signal goes from 0V (low) to 3.3V (high), so we count on rising edge
        self.motor_rpm_pin.irq(trigger=Pin.IRQ_RISING, handler=self._motor_pulse_handler)
        
        # Motor stop trigger on GPIO pin (goes HIGH when motor crank is at bottom position)
        self.motor_stop_pin = Pin(motor_stop_gpio_pin, Pin.IN, Pin.PULL_UP)
        self.motor_crank_pulse_count = 0  # Total pulse count for motor crank rotations
        # Set up interrupt handler for motor stop trigger (trigger on rising edge when pin goes HIGH)
        self.motor_stop_pin.irq(trigger=Pin.IRQ_RISING, handler=self._motor_crank_pulse_handler)
    
    def _motor_pulse_handler(self, _pin):
        """Interrupt handler for motor RPM hall sensor pulses.
        
        Optimized for fast pulses - minimal code in interrupt handler.
        Signal transitions from 0V (low) to 3.3V (high) for each rotation.
        
        Args:
            _pin: The pin that triggered the interrupt (unused but required by MicroPython).
        """
        # Minimal interrupt handler - just increment counter
        # Using +=1 is atomic enough for interrupt context
        self.motor_pulse_count += 1
        # Track motor rotations since last motor crank pulse (for position calculation)
        self.motor_count_since_last_motor_crank += 1
        # Wrap around at 1000 (one full motor crank rotation)
        if self.motor_count_since_last_motor_crank >= self.motor_rotations_per_motor_crank:
            self.motor_count_since_last_motor_crank = 0
    
    def _motor_crank_pulse_handler(self, _pin):
        """Interrupt handler for motor crank rotation sensor pulses.
        
        Optimized for fast pulses - minimal code in interrupt handler.
        Signal transitions from 0V (low) to 3.3V (high) when motor crank is at bottom of rotation.
        Resets motor count since last motor crank pulse.
        
        Args:
            _pin: The pin that triggered the interrupt (unused but required by MicroPython).
        """
        # Minimal interrupt handler - just increment counter
        # Using +=1 is atomic enough for interrupt context
        self.motor_crank_pulse_count += 1
        # Reset motor count since last motor crank pulse (motor crank is at bottom, 0 degrees)
        self.motor_count_since_last_motor_crank = 0
    
    def get_pulse_count(self):
        """Get the current motor pulse count.
        
        Returns:
            Total number of pulses detected (1 pulse per full 360 rotation).
        """
        return self.motor_pulse_count
    
    def get_motor_crank_count(self):
        """Get the current motor crank rotation count.
        
        Returns:
            Total number of motor crank rotations detected (1 pulse per full 360 rotation).
        """
        return self.motor_crank_pulse_count
    
    def reset_count(self):
        """Reset the motor pulse count to zero."""
        self.motor_pulse_count = 0
    
    def reset_motor_crank_count(self):
        """Reset the motor crank pulse count to zero."""
        self.motor_crank_pulse_count = 0
    
    def get_motor_crank_position(self):
        """Get the current motor crank position based on motor rotations.
        
        Motor stop pin is HIGH when motor crank is at bottom (0 degrees).
        1000 motor rotations = 1 full motor crank rotation (360 degrees).
        500 motor rotations = motor crank at top (180 degrees).
        
        Returns:
            Motor crank position in degrees (0-360), where 0 = bottom, 180 = top.
        """
        # Calculate position: motor_count_since_last_motor_crank / motor_rotations_per_motor_crank * 360
        position_degrees = (self.motor_count_since_last_motor_crank / self.motor_rotations_per_motor_crank) * 360.0
        return position_degrees
    
    def get_motor_crank_position_percent(self):
        """Get the current motor crank position as a percentage of full rotation.
        
        Returns:
            Motor crank position as percentage (0.0-100.0), where 0.0 = bottom, 50.0 = top.
        """
        return (self.motor_count_since_last_motor_crank / self.motor_rotations_per_motor_crank) * 100.0
    
    def is_motor_crank_at_bottom(self):
        """Check if the motor crank is currently at its lowest position (bottom).
        
        Reads the motor stop trigger pin state. The pin is HIGH when motor crank is at bottom.
        This can be used to validate or reset the position tracking.
        
        Returns:
            True if motor stop pin is HIGH (motor crank at bottom), False otherwise.
        """
        return self.motor_stop_pin.value() == 1
    
    def sync_position_to_sensor(self):
        """Synchronize position tracking with the motor stop sensor.
        
        If the motor stop sensor indicates the motor crank is at bottom, reset the motor count
        since last motor crank pulse to ensure accurate position tracking.
        
        Returns:
            True if position was synced (motor crank was at bottom), False otherwise.
        """
        if self.is_motor_crank_at_bottom():
            self.motor_count_since_last_motor_crank = 0
            return True
        return False
    
    def update_display(self, lcd, rgb_color_func, back_col, start_y=None):
        """Update the motor and motor crank count display on the LCD.
        
        Args:
            lcd: LCD display object to update.
            rgb_color_func: Function to convert RGB values to display color.
            back_col: Background color for the display area.
            start_y: Starting Y position for display (default: None, will calculate from screen height).
        """
        # Calculate starting position if not provided
        if start_y is None:
            start_y = self.screen_height - 60  # Default to bottom area
        
        # Get current counts
        motor_pulse_count = self.get_pulse_count()
        motor_crank_pulse_count = self.get_motor_crank_count()
        
        # Font settings
        char_width_base = 8
        font_size = 2
        char_width = char_width_base * font_size
        line_spacing = 18
        
        # Display motor count
        motor_text = "Motor: " + str(motor_pulse_count)
        motor_text_width = len(motor_text) * char_width
        motor_x = (self.screen_width - motor_text_width) // 2
        motor_y = start_y
        
        # Display motor crank count below motor count
        motor_crank_text = "MCrank: " + str(motor_crank_pulse_count)
        motor_crank_text_width = len(motor_crank_text) * char_width
        motor_crank_x = (self.screen_width - motor_crank_text_width) // 2
        motor_crank_y = motor_y + line_spacing
        
        # Color for text
        text_color = rgb_color_func(200, 200, 200)
        
        # Clear display area (enough for 2 lines)
        display_height = line_spacing * 2 + 10
        lcd.fill_rect(0, motor_y, self.screen_width, display_height, back_col)
        
        # Display motor count
        if text_color is not None and motor_x is not None and motor_y is not None:
            lcd.write_text(motor_text, int(motor_x), int(motor_y), font_size, int(text_color))
        
        # Display motor crank count
        if text_color is not None and motor_crank_x is not None and motor_crank_y is not None:
            lcd.write_text(motor_crank_text, int(motor_crank_x), int(motor_crank_y), font_size, int(text_color))
