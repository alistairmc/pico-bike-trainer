from machine import Pin


class MotorSensor:
    """Motor sensor class for reading and counting motor RPM.
    
    This class handles hall sensor-based motor RPM readings (1 pulse per full 360 rotation).
    Uses GPIO pins with interrupt handlers to count rotations when pins go high.
    """
    
    def __init__(self, motor_count_gpio_pin=0, motor_stop_gpio_pin=1):
        """Initialize the motor sensor.
        
        Args:
            motor_count_gpio_pin: GPIO pin number for the motor hall sensor (default: 0).
            motor_stop_gpio_pin: GPIO pin number for the motor stop trigger (default: 1).
        """
        self.motor_count_gpio_pin = motor_count_gpio_pin
        self.motor_stop_gpio_pin = motor_stop_gpio_pin
        self.motor_rpm_pin = Pin(motor_count_gpio_pin, Pin.IN, Pin.PULL_UP)
        self.motor_pulse_count = 0  # Total pulse count for motor RPM
        self.motor_rotations_per_motor_crank = 1000  # 1000 motor rotations = 1 full motor crank rotation
        self.motor_crank_position = 0  # Motor crank position (0-1000, representing 0-360 degrees)
        self.motor_direction = 1  # 1 = forward (increment), -1 = reverse (decrement)
        
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
        Increments or decrements counters based on motor direction.
        
        Args:
            _pin: The pin that triggered the interrupt (unused but required by MicroPython).
        """
        # Update counters based on direction
        # Using += and -= are atomic enough for interrupt context
        self.motor_pulse_count += self.motor_direction
        # Update motor crank position (can be negative or positive)
        # Position 0 = stop position (0% load)
        # Position +500 = 180 degrees forward (100% load)
        # Position -500 = 180 degrees reverse (100% load)
        self.motor_crank_position += self.motor_direction
        
        # Handle wrapping/clamping for motor_crank_position
        # Allow positions from -500 to +500 for load control (180 degrees either way from 0)
        max_load_position = self.motor_rotations_per_motor_crank // 2  # 500
        if self.motor_direction == 1:  # Forward
            # Forward: wrap at full rotation (1000) back to 0
            if self.motor_crank_position >= self.motor_rotations_per_motor_crank:
                self.motor_crank_position = 0
            # Clamp to max load position if going too far forward (beyond 500)
            elif self.motor_crank_position > max_load_position:
                self.motor_crank_position = max_load_position
        else:  # Reverse
            # Reverse: clamp to -500 (max load in reverse direction)
            if self.motor_crank_position < -max_load_position:
                self.motor_crank_position = -max_load_position
    
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
        # Reset motor crank position (motor crank is at bottom, 0 degrees)
        self.motor_crank_position = 0
    
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
        """Get the current motor crank position in degrees (0-180 for load).
        
        Position 0 = 0 degrees (bottom position, least resistance, stop position)
        Position +500 = 180 degrees (top position, most resistance, forward)
        Position -500 = 180 degrees (top position, most resistance, reverse)
        Both +500 and -500 represent the same load (180 degrees either way from 0).
        
        Returns:
            Motor crank position in degrees (0-180), where 0 = bottom, 180 = top.
        """
        # Use absolute position for degree calculation
        # Both +500 and -500 represent 180 degrees (same load)
        position_abs = abs(self.motor_crank_position)
        max_load_position = self.motor_rotations_per_motor_crank // 2  # 500
        
        # Clamp to 180 degrees max (100% load)
        if position_abs > max_load_position:
            position_abs = max_load_position
        
        position_degrees = (position_abs / max_load_position) * 180.0
        return position_degrees
    
    def get_motor_crank_position_percent(self):
        """Get the current motor crank position as a percentage of full rotation.
        
        Uses absolute position since both +500 and -500 represent the same load.
        
        Returns:
            Motor crank position as percentage (0.0-100.0), where 0.0 = bottom, 50.0 = top.
        """
        # Use absolute position for percentage calculation
        position_abs = abs(self.motor_crank_position)
        max_load_position = self.motor_rotations_per_motor_crank // 2  # 500
        
        # Clamp to max load position
        if position_abs > max_load_position:
            position_abs = max_load_position
        
        # Calculate as percentage of 180 degrees (0-100% load range)
        return (position_abs / max_load_position) * 100.0
    
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
            self.motor_crank_position = 0
            return True
        return False
    
    def disable_stop_interrupt(self):
        """Disable the motor stop trigger interrupt handler.
        
        Useful during calibration to avoid false positives from interrupt noise.
        """
        self.motor_stop_pin.irq(handler=None)
    
    def enable_stop_interrupt(self):
        """Re-enable the motor stop trigger interrupt handler."""
        self.motor_stop_pin.irq(trigger=Pin.IRQ_RISING, handler=self._motor_crank_pulse_handler)
    
    def set_motor_direction_forward(self):
        """Set motor direction to forward (counts increment)."""
        self.motor_direction = 1
    
    def set_motor_direction_reverse(self):
        """Set motor direction to reverse (counts decrement)."""
        self.motor_direction = -1
    
