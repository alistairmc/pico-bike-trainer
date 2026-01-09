from machine import Pin
import utime


class LoadController:
    """Load controller class for applying resistance using L298N motor controller.
    
    This class controls an L298N motor controller to move magnets closer/farther from
    the wheel to apply resistance, simulating both gear-based resistance
    (lower gears easier, higher gears harder) and incline/decline resistance.
    Uses direction control only (no speed control).
    """
    
    def __init__(self, l298n_in1_pin, l298n_in2_pin, gear_selector=None, base_load_factor=1.0, motor_sensor=None, lcd=None, rgb_color_func=None):
        """Initialize the load controller.
        
        Args:
            l298n_in1_pin: GPIO pin number for L298N IN1 direction control.
            l298n_in2_pin: GPIO pin number for L298N IN2 direction control.
            gear_selector: GearSelector instance to get current gear ratio (default: None).
            base_load_factor: Base load multiplier for gear resistance (default: 1.0).
            motor_sensor: MotorSensor instance to track motor crank position (default: None).
            lcd: LCD display object for calibration status (default: None).
            rgb_color_func: Function to convert RGB values to display color (default: None).
        """
        # L298N motor controller pins (direction control only, no speed control)
        self.l298n_in1_pin = Pin(l298n_in1_pin, Pin.OUT)
        self.l298n_in2_pin = Pin(l298n_in2_pin, Pin.OUT)
        
        # Initialize motor to stopped state
        self.stop_motor()
        
        self.gear_selector = gear_selector
        self.motor_sensor = motor_sensor
        self.base_load_factor = base_load_factor
        self.lcd = lcd
        self.rgb_color_func = rgb_color_func
        
        # Motor control state
        self.current_direction = None  # None = stopped, True = forward (increase load), False = reverse (decrease load)
        self.incline_percent = 0.0  # Current incline/decline (-100 to +100)
        self.motor_is_running = False  # Track if motor is currently running
        self.last_load_update_time = 0  # Track when load was last updated
        
        # Motor control timing
        self.motor_run_time_ms = 100  # Time to run motor when adjusting load (milliseconds)
        self.min_load_update_interval_ms = 150  # Minimum time between load updates (allow position to update)
    
    def _display_calibration_status(self, status_text, detail_text=None):
        """Display calibration status on the LCD if available.
        
        Args:
            status_text: Main status message to display.
            detail_text: Optional detail message to display below main status.
        """
        if self.lcd is None or self.rgb_color_func is None:
            return  # No display available
        
        # Clear the entire screen
        self.lcd.fill(0)  # Black background
        
        # Calculate text positions (centered)
        text_color = self.rgb_color_func(255, 255, 255)  # White text
        title_color = self.rgb_color_func(255, 200, 0)  # Yellow/orange for title
        
        # Title
        title = "CALIBRATION"
        title_size = 3
        title_char_width = 8 * title_size
        title_width = len(title) * title_char_width
        title_x = max(0, (240 - title_width) // 2)
        title_y = 20
        
        try:
            if title_color is not None:
                self.lcd.write_text(title, int(title_x), title_y, title_size, int(title_color))
        except (TypeError, ValueError, AttributeError):
            pass
        
        # Main status text
        status_size = 2
        status_char_width = 8 * status_size
        status_width = len(status_text) * status_char_width
        status_x = max(0, (240 - status_width) // 2)
        status_y = 80
        
        try:
            if text_color is not None:
                self.lcd.write_text(status_text, int(status_x), status_y, status_size, int(text_color))
        except (TypeError, ValueError, AttributeError):
            pass
        
        # Detail text (if provided)
        if detail_text:
            detail_size = 2
            detail_char_width = 8 * detail_size
            detail_width = len(detail_text) * detail_char_width
            detail_x = max(0, (240 - detail_width) // 2)
            detail_y = 120
            
            try:
                if text_color is not None:
                    self.lcd.write_text(detail_text, int(detail_x), detail_y, detail_size, int(text_color))
            except (TypeError, ValueError, AttributeError):
                pass
        
        # Show the display
        self.lcd.show()
    
    def _wait_for_stop_trigger(self, timeout_ms=600000):
        """Wait for motor stop trigger and stop at start of pulse.
        
        The stop trigger has a wide pulse, so we:
        1. Wait for pin to go HIGH (start of pulse)
        2. Stop immediately when pulse is detected (debounced)
        
        Args:
            timeout_ms: Maximum time to wait in milliseconds.
            
        Returns:
            True if stop trigger detected, False if timeout.
        """
        if self.motor_sensor is None:
            return False
        
        # Wait for pin to go HIGH (start of wide pulse) with debouncing
        debounce_count = 0
        required_high_readings = 10  # Require 10 consecutive HIGH readings (100ms) to detect pulse start
        start_time = utime.ticks_ms()
        
        # Wait for pulse to start
        while debounce_count < required_high_readings:
            if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout_ms:
                return False
            
            pin_value = self.motor_sensor.motor_stop_pin.value()
            if pin_value == 1:  # HIGH - pulse started
                debounce_count += 1
            else:
                debounce_count = 0
            
            utime.sleep_ms(10)
        
        # Pulse detected - return True to stop motor
        return True
    
    def startup_calibration(self):
        """Perform startup sequence to move motor to stop position.
        
        Uses fixed ratio of 1000 motor rotations per motor crank rotation.
        Moves motor to stop position (0 degrees) on startup.
        """
        if self.motor_sensor is None:
            print("Startup ERROR: Motor sensor not initialized")
            self._display_calibration_status("ERROR", "No motor sensor")
            return  # Can't proceed without motor sensor
        
        # Clear display and show initial status
        self._display_calibration_status("Initializing...", "Checking sensors")
        utime.sleep_ms(500)  # Brief pause to show message
        
        # Ensure motor_rotations_per_motor_crank is set to 1000 (should already be default)
        self.motor_sensor.motor_rotations_per_motor_crank = 1000
        
        # Temporarily disable the interrupt handler to avoid false positives
        self.motor_sensor.disable_stop_interrupt()
        
        print("Startup: Moving to stop position...")
        print(f"Startup: Initial GPIO 0 (motor count) state: {self.motor_sensor.motor_rpm_pin.value()}")
        print(f"Startup: Initial GPIO 1 (motor stop) state: {self.motor_sensor.motor_stop_pin.value()}")
        print(f"Startup: Initial pulse count: {self.motor_sensor.motor_pulse_count}")
        
        self._display_calibration_status("Starting...", "Moving to stop")
        
        # Check if motor is already at stop position
        initial_stop_state = self.motor_sensor.motor_stop_pin.value() == 1
        
        if initial_stop_state:
            print("Startup: Motor already at stop position, moving back first...")
            self._display_calibration_status("Step 1/2", "Moving away from stop")
            # Motor is already at stop, move it back (reverse) until not in stop position
            self.set_motor_direction_reverse()
            
            # Monitor if motor is actually moving by checking pulse count
            initial_pulse_count = self.motor_sensor.motor_pulse_count
            last_pulse_check_time = utime.ticks_ms()
            pulse_check_interval = 2000  # Check every 2 seconds
            
            # Wait for pin to go LOW (move off stop position)
            debounce_count = 0
            required_low_readings = 10
            timeout_ms = 30000  # 30 second timeout
            start_time = utime.ticks_ms()
            
            while debounce_count < required_low_readings:
                elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
                if elapsed > timeout_ms:
                    print(f"Startup ERROR: Could not move off stop position after {elapsed}ms")
                    print(f"Startup: Final pulse count: {self.motor_sensor.motor_pulse_count} (was {initial_pulse_count})")
                    if self.motor_sensor.motor_pulse_count == initial_pulse_count:
                        print("Startup ERROR: Motor sensor (GPIO 0) not detecting any pulses!")
                        print("Startup: Check motor sensor connections and alignment")
                        self._display_calibration_status("ERROR", "Sensor not working")
                    else:
                        self._display_calibration_status("ERROR", "Timeout moving")
                    self.stop_motor()
                    self.motor_sensor.enable_stop_interrupt()
                    return
                
                # Check if motor is moving (pulses detected)
                if utime.ticks_diff(utime.ticks_ms(), last_pulse_check_time) >= pulse_check_interval:
                    current_pulses = self.motor_sensor.motor_pulse_count
                    if current_pulses == initial_pulse_count:
                        print(f"Startup WARNING: No motor pulses detected after {elapsed}ms - motor may be stuck or sensor not working")
                        self._display_calibration_status("Step 1/2", "No pulses detected!")
                    else:
                        print(f"Startup: Motor moving - {current_pulses - initial_pulse_count} pulses detected")
                        pulse_count = current_pulses - initial_pulse_count
                        self._display_calibration_status("Step 1/2", f"Moving: {pulse_count} pulses")
                    last_pulse_check_time = utime.ticks_ms()
                
                pin_value = self.motor_sensor.motor_stop_pin.value()
                if pin_value == 0:  # LOW - moved off stop
                    debounce_count += 1
                else:
                    debounce_count = 0
                
                utime.sleep_ms(10)
            
            # Continue moving a bit more to ensure we're clear of the stop
            print("Startup: Moving additional 2 seconds to clear stop position...")
            utime.sleep_ms(2000)  # Move for additional 2000ms (2 seconds)
            self.stop_motor()
            utime.sleep_ms(200)
            
            # Reset motor counts after moving back from initial stop
            self.motor_sensor.motor_pulse_count = 0
            self.motor_sensor.motor_crank_position = 0
            print("Startup: Moved off stop position, counts reset, now moving forward to find stop trigger...")
        
        # Move motor forward until stop trigger is detected
        print("Startup: Moving forward to find stop trigger...")
        self._display_calibration_status("Step 2/2", "Finding stop position")
        self.set_motor_direction_forward()
        
        # Monitor motor movement while waiting for stop trigger
        initial_pulse_count = self.motor_sensor.motor_pulse_count
        last_pulse_check_time = utime.ticks_ms()
        pulse_check_interval = 5000  # Check every 5 seconds
        
        # Modified wait function with movement monitoring
        debounce_count = 0
        required_high_readings = 10
        timeout_ms = 600000  # 10 minute timeout to allow for up to 1000 motor rotations
        start_time = utime.ticks_ms()
        
        while debounce_count < required_high_readings:
            elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
            if elapsed > timeout_ms:
                print(f"Startup ERROR: Stop trigger not detected after {elapsed}ms")
                print(f"Startup: Final pulse count: {self.motor_sensor.motor_pulse_count} (was {initial_pulse_count})")
                if self.motor_sensor.motor_pulse_count == initial_pulse_count:
                    print("Startup ERROR: Motor sensor (GPIO 0) not detecting any pulses!")
                    print("Startup: Check motor sensor connections and alignment")
                    self._display_calibration_status("ERROR", "Sensor not working")
                else:
                    print("Startup ERROR: Motor stop trigger (GPIO 1) not detected!")
                    print("Startup: Check stop sensor connections and alignment")
                    self._display_calibration_status("ERROR", "Stop trigger failed")
                self.stop_motor()
                self.motor_sensor.enable_stop_interrupt()
                return
            
            # Check if motor is moving (pulses detected)
            if utime.ticks_diff(utime.ticks_ms(), last_pulse_check_time) >= pulse_check_interval:
                current_pulses = self.motor_sensor.motor_pulse_count
                pulse_diff = current_pulses - initial_pulse_count
                if pulse_diff == 0:
                    print(f"Startup WARNING: No motor pulses detected after {elapsed}ms - motor may be stuck or sensor not working")
                    self._display_calibration_status("Step 2/2", "No pulses detected!")
                else:
                    print(f"Startup: Motor moving - {pulse_diff} pulses detected, elapsed: {elapsed}ms")
                    self._display_calibration_status("Step 2/2", f"Moving: {pulse_diff} pulses")
                last_pulse_check_time = utime.ticks_ms()
            
            pin_value = self.motor_sensor.motor_stop_pin.value()
            if pin_value == 1:  # HIGH - pulse started
                debounce_count += 1
            else:
                debounce_count = 0
            
            utime.sleep_ms(10)
        
        # Stop trigger detected
        elapsed = utime.ticks_ms() - start_time
        final_pulses = self.motor_sensor.motor_pulse_count
        print(f"Startup: Stop trigger detected after {elapsed}ms, {final_pulses - initial_pulse_count} pulses")
        
        self._display_calibration_status("Complete!", "Stopping motor")
        
        # Stop motor at start of stop pulse
        self.stop_motor()
        utime.sleep_ms(300)  # Pause to ensure motor stops
        
        # Sync position to sensor (reset count to 0)
        self.motor_sensor.sync_position_to_sensor()
        
        # Re-enable interrupt handler
        self.motor_sensor.enable_stop_interrupt()
        
        print("Startup: Motor at stop position, ready")
        self._display_calibration_status("Ready!", "Calibration complete")
        utime.sleep_ms(1000)  # Show completion message for 1 second
    
    def set_incline(self, incline_percent):
        """Set the incline/decline percentage.
        
        Args:
            incline_percent: Incline percentage (-100 to +100).
                            Negative values = decline (easier),
                            Positive values = incline (harder),
                            0 = flat road.
        """
        self.incline_percent = max(-100.0, min(100.0, incline_percent))
        self._update_load()
    
    def get_incline(self):
        """Get the current incline/decline percentage.
        
        Returns:
            Current incline percentage (-100 to +100).
        """
        return self.incline_percent
    
    def _calculate_base_load(self):
        """Calculate base load based on current gear ratio.
        
        First gear with no hill = 50% load = 90 degrees (baseline).
        Higher gears increase load, lower gears decrease load.
        This allows hills and gears to adjust from the 50% baseline.
        
        Returns:
            Base load value based on gear ratio (25 to 75, first gear = 50).
        """
        if self.gear_selector is not None:
            current_ratio = self.gear_selector.get_current_ratio()
            min_ratio = self.gear_selector.min_ratio
            max_ratio = self.gear_selector.max_ratio
            
            # Normalize ratio to 0-1 range
            if max_ratio > min_ratio:
                normalized_ratio = (current_ratio - min_ratio) / (max_ratio - min_ratio)
            else:
                normalized_ratio = 0.0  # Default to first gear if ratios are same
            
            # Map normalized ratio to 25-75 range:
            # First gear (normalized_ratio = 0) = 50 (50% load = 90 degrees)
            # Higher gears (normalized_ratio > 0) = 50 to 75 (increase load)
            # This gives room for incline to add/subtract ±25 from gear baseline
            # First gear starts at 50, so it can go down to 25 (with decline) or up to 75 (with incline)
            base_load = 50.0 + (normalized_ratio * 25.0)  # First gear = 50, last gear = 75
            
            return base_load * self.base_load_factor
        else:
            # No gear selector, use baseline (50 = 50% = 90 degrees)
            return 50.0 * self.base_load_factor
    
    def _calculate_incline_load(self):
        """Calculate load contribution from incline/decline.
        
        Returns:
            Incline load value (-25 to +25).
            This allows incline to adjust ±25% from the gear baseline.
            First gear (50) can go from 25 (with -100% decline) to 75 (with +100% incline).
        """
        # Incline adds resistance, decline reduces it
        # Convert percentage to load adjustment (-25 to +25)
        # This gives ±25% adjustment range from the gear baseline
        return (self.incline_percent / 100.0) * 25.0
    
    def set_motor_direction_forward(self):
        """Set L298N motor direction to forward.
        
        IN1 = HIGH, IN2 = LOW -> Forward direction.
        Moves magnet closer to flywheel (increases resistance).
        """
        self.l298n_in1_pin.value(1)
        self.l298n_in2_pin.value(0)
        self.current_direction = True
        # Update motor sensor direction
        if self.motor_sensor is not None:
            self.motor_sensor.set_motor_direction_forward()
    
    def set_motor_direction_reverse(self):
        """Set L298N motor direction to reverse.
        
        IN1 = LOW, IN2 = HIGH -> Reverse direction.
        Moves magnet further from flywheel (decreases resistance).
        """
        self.l298n_in1_pin.value(0)
        self.l298n_in2_pin.value(1)
        self.current_direction = False
        # Update motor sensor direction
        if self.motor_sensor is not None:
            self.motor_sensor.set_motor_direction_reverse()
    
    def stop_motor(self):
        """Stop the L298N motor.
        
        IN1 = LOW, IN2 = LOW -> Stop (coast).
        """
        self.l298n_in1_pin.value(0)
        self.l298n_in2_pin.value(0)
        self.current_direction = None
    
    def brake_motor(self):
        """Brake the L298N motor.
        
        IN1 = HIGH, IN2 = HIGH -> Brake (short circuit).
        """
        self.l298n_in1_pin.value(1)
        self.l298n_in2_pin.value(1)
        self.current_direction = None
    
    def _move_motor_to_position(self, target_position, forward=True):
        """Move motor until motor_crank_position reaches target position.
        
        Args:
            target_position: Target motor crank position (can be negative or positive, -500 to +500).
            forward: True to move forward, False to move reverse.
        """
        if self.motor_sensor is None or self.motor_is_running:
            return
        
        self.motor_is_running = True
        
        if forward:
            self.set_motor_direction_forward()
        else:
            self.set_motor_direction_reverse()
        
        # Wait until we reach target position
        timeout_ms = 30000  # 30 second timeout
        start_time = utime.ticks_ms()
        
        # Wait until we reach target position (allowing negative positions)
        while True:
            if utime.ticks_diff(utime.ticks_ms(), start_time) > timeout_ms:
                break
            current_position = self.motor_sensor.motor_crank_position
            
            # Check if we've reached target (within tolerance)
            position_diff = abs(target_position - current_position)
            if position_diff <= 5:  # Within 5 position units (tolerance)
                break
            utime.sleep_ms(10)
        
        self.stop_motor()
        self.motor_is_running = False
    
    def _run_motor_timed(self, direction, duration_ms=None):
        """Run the motor in a specific direction for a set duration.
        
        Args:
            direction: True = forward (increase load), False = reverse (decrease load).
            duration_ms: Duration to run motor in milliseconds (default: self.motor_run_time_ms).
        """
        if duration_ms is None:
            duration_ms = self.motor_run_time_ms
        
        # Don't start if motor is already running
        if self.motor_is_running:
            return
        
        self.motor_is_running = True
        
        if direction:
            self.set_motor_direction_forward()
        else:
            self.set_motor_direction_reverse()
        
        utime.sleep_ms(duration_ms)
        self.stop_motor()
        self.motor_is_running = False
    
    def _update_load(self):
        """Update the motor direction based on current gear and incline.
        
        Total load = base_load (from gear) + incline_load
        Higher load = magnets closer to wheel = run motor forward
        Lower load = magnets further from wheel = run motor reverse
        
        Since counter is reset after startup, we can move a set number of motor rotations
        to reach the target position directly.
        """
        base_load = self._calculate_base_load()
        incline_load = self._calculate_incline_load()
        
        # Combine loads (base load is always positive, incline can be negative)
        total_load = base_load + incline_load
        
        # Clamp to 0-100 range (load percentage)
        total_load = max(0.0, min(100.0, total_load))
        
        # Quantize load to 5% increments (0, 5, 10, ..., 100)
        # This provides granular control in 5% steps
        total_load = round(total_load / 5.0) * 5.0  # Round to nearest 5%
        
        # If we have a motor sensor, move motor to target position
        if self.motor_sensor is not None:
            # Target position: 0 degrees = 0% load, 180 degrees = 100% load
            # Position 0 = 0% load, position 500 (forward) = 100% load, position -500 (reverse) = 100% load
            # Calculate target motor crank position: (target_degrees / 180) * 500
            # 500 represents 180 degrees (half of 1000 rotations per full crank rotation)
            target_degrees = (total_load / 100.0) * 180.0  # Convert 0-100% to 0-180 degrees
            max_load_position = self.motor_sensor.motor_rotations_per_motor_crank // 2  # 500 for 180 degrees
            target_position_abs = int((target_degrees / 180.0) * max_load_position)  # 0 to 500
            
            # Get current motor crank position (can be negative or positive)
            current_position = self.motor_sensor.motor_crank_position
            current_abs = abs(current_position)
            
            # Calculate current load based on absolute position
            current_load = (current_abs / max_load_position) * 100.0 if max_load_position > 0 else 0.0
            current_load = min(100.0, current_load)  # Clamp to 100%
            
            # Determine if we're increasing or decreasing load
            is_increasing_load = total_load > current_load
            
            # Choose target position (positive or negative) based on current position and direction
            # If increasing load and current is negative, prefer positive target
            # If decreasing load and current is positive, prefer negative target
            # Otherwise, choose direction that doesn't go wrong way first
            if is_increasing_load:
                # Increasing load: prefer forward (positive) if current is at or near 0
                # If current is negative, move forward to positive
                if current_position <= 0:
                    target_position = target_position_abs  # Forward to positive
                else:
                    # Current is positive, move forward to higher positive
                    target_position = target_position_abs
            else:
                # Decreasing load: prefer reverse (negative) if current is at or near 0
                # If current is positive, move reverse to negative
                if current_position >= 0:
                    target_position = -target_position_abs  # Reverse to negative
                else:
                    # Current is negative, move reverse to higher negative (closer to 0)
                    target_position = -target_position_abs
            
            # Calculate distance to target
            position_diff = abs(target_position - current_position)
            
            # Determine direction to move
            if target_position > current_position:
                use_forward = True
            else:
                use_forward = False
            
            # Only move if difference is significant (more than 5 position units = ~1.8 degrees)
            # Don't move if motor is already running
            if position_diff > 5 and not self.motor_is_running:
                # Move in the correct direction (forward to increase, reverse to decrease)
                self._move_motor_to_position(target_position, forward=use_forward)
            else:
                # Close enough to target or motor already running, stop motor
                if not self.motor_is_running:
                    self.stop_motor()
        else:
            # No motor sensor, use simple load-based control
            # Higher load = run forward, lower load = run reverse
            if total_load > 50.0:
                # Above 50% load, run forward to increase
                self._run_motor_timed(True)
            elif total_load < 50.0:
                # Below 50% load, run reverse to decrease
                self._run_motor_timed(False)
            else:
                # At 50% load, stop
                self.stop_motor()
    
    def apply_load(self):
        """Apply the calculated load based on current gear and incline.
        
        This should be called whenever the gear changes or incline is updated.
        Moves the stepper motor to position magnets at the correct distance.
        """
        self._update_load()
    
    def remove_load(self):
        """Remove all load (set to zero).
        
        Moves magnets to farthest position, effectively removing all resistance.
        Runs motor in reverse direction.
        """
        self._run_motor_timed(False, duration_ms=500)  # Run longer to fully remove load
    
    def set_load(self, load_percent):
        """Set the load directly as a percentage.
        
        Args:
            load_percent: Load percentage (0.0 to 1.0).
        """
        # This will be handled by _update_load() based on motor crank position
        # For now, just update the incline to achieve the desired load
        # This is a simplified approach - in practice, you'd want more sophisticated control
        pass
    
    def get_current_load_percent(self):
        """Return the current load as a percentage (0.0 to 100.0).
        
        Returns:
            Current load percentage based on motor crank position or estimated load.
        """
        if self.motor_sensor is not None:
            # Calculate load based on absolute motor crank position
            # Position 0 = 0% load, position 500 (forward) or -500 (reverse) = 180 degrees = 100% load
            # Both +500 and -500 represent the same load (180 degrees either way from 0)
            position = self.motor_sensor.motor_crank_position
            position_abs = abs(position)
            max_load_position = self.motor_sensor.motor_rotations_per_motor_crank // 2  # 500 for 180 degrees
            load = (position_abs / max_load_position) * 100.0 if max_load_position > 0 else 0.0
            return max(0.0, min(100.0, load))  # Clamp to 0-100%
        
        # No motor sensor, return estimated load based on gear and incline
        base_load = self._calculate_base_load()
        incline_load = self._calculate_incline_load()
        total_load = base_load + incline_load
        return max(0.0, min(100.0, total_load))

