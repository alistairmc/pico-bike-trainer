from machine import Pin
import utime


class SpeedSensor:
    """Speed sensor class for reading and displaying speed.
    
    This class handles hall sensor-based speed readings and provides
    methods to read speed values and update the display.
    """
    
    def __init__(self, gpio_pin=None, gear_selector=None, load_controller=None, screen_width=240, screen_height=240, display_x=None, display_y=None, unit='kmph'):
        """Initialize the speed sensor.
        
        Args:
            gpio_pin: GPIO pin number for the hall sensor (default: None for mock mode).
            gear_selector: GearSelector instance to get current gear ratio (default: None).
            load_controller: LoadController instance to get current load (default: None).
            screen_width: Width of the display screen in pixels (default: 240).
            screen_height: Height of the display screen in pixels (default: 240).
            display_x: X coordinate for speed display (default: 0).
            display_y: Y coordinate for speed display (default: screen_height - 60).
            unit: Speed unit to display - 'kmph' for km/h or 'mph' for mph (default: 'kmph').
        """
        self.gear_selector = gear_selector
        self.load_controller = load_controller
        self.gpio_pin = gpio_pin
        # Initialize pulse tracking (used for both real and simulated pulses)
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.pulse_times = []  # Store recent pulse times for pedal speed calculation
        self.wheel_circumference = 2.1  # meters (typical bike wheel)
        self.calibration_factor = 1.0  # Calibration factor to adjust speed calculation
        self.sample_window_ms = 1000  # 1 second window for speed calculation
        
        if gpio_pin is not None:
            self.hall_sensor = Pin(gpio_pin, Pin.IN, Pin.PULL_UP)
            # Note: GPIO reads pedal speed (cadence), not wheel speed
            # Set up interrupt handler for pulse counting
            self.hall_sensor.irq(trigger=Pin.IRQ_FALLING, handler=self._pulse_handler)
        else:
            self.hall_sensor = None
            # Mock mode - will use simulated speed or manual pulses
        
        self.unit = unit.lower()  # Store unit preference (kmph or mph)
        self.last_displayed_speed = None  # Track last displayed speed
        self.last_read_speed = None  # Track last read speed (always in km/h internally)
        self.screen_width = screen_width
        self.screen_height = screen_height
        # Set display position (default to top of screen if not specified)
        self.display_x = display_x if display_x is not None else 0
        self.display_y = display_y if display_y is not None else 0
        # Calculate positions for label and speed value
        self.label_y = self.display_y
        self.speed_y = self.display_y + 30  # Speed value below label
        
        # Simulated RPM control (off by default)
        self.simulated_rpm_enabled = False
        self.target_rpm = 10  # Current target RPM for simulated pulses
        # Don't initialize pulses by default (simulated RPM is off)
    
    def _initialize_default_pulses(self, rpm):
        """Initialize pulse_times with pulses simulating a given RPM.
        
        Args:
            rpm: Target RPM (revolutions per minute) to simulate.
        """
        current_time = utime.ticks_ms()
        
        # Calculate time between pulses for the given RPM
        # RPM = revolutions per minute, so time per revolution = 60 / RPM seconds
        # Convert to milliseconds
        if rpm > 0:
            time_per_revolution_ms = (60.0 / rpm) * 1000.0
            
            # Generate pulses - always generate at least 2 pulses for speed calculation
            # If time between pulses is longer than sample window, extend the window
            # to ensure we have at least 2 pulses
            if time_per_revolution_ms > self.sample_window_ms:
                # For low RPM, we need to extend the window to fit 2 pulses
                # Use 2 revolutions worth of time to capture 10 RPM (6 sec/rev = 12 sec for 2 revs)
                # Max extended window: 15 seconds to support down to 8 RPM
                extended_window = min(2 * time_per_revolution_ms, 15000)  # Max 15 seconds
                num_pulses = 2
            else:
                # Normal case: calculate how many pulses fit in sample window
                num_revolutions = int(self.sample_window_ms / time_per_revolution_ms)
                num_pulses = max(2, num_revolutions + 1)
                extended_window = self.sample_window_ms
            
            # Generate pulses going backwards from current time at exact intervals
            # This ensures consistent spacing for accurate speed calculation
            for i in range(num_pulses):
                pulse_time = current_time - (i * time_per_revolution_ms)
                # Add pulses within the extended window
                if pulse_time >= (current_time - extended_window):
                    self.pulse_times.append(int(pulse_time))
                    self.pulse_count += 1
            
            # Sort pulses to ensure they're in chronological order
            self.pulse_times.sort()
    
    def _pulse_handler(self, _pin):
        """Interrupt handler for hall sensor pulses.
        
        Args:
            _pin: The pin that triggered the interrupt (unused but required by MicroPython).
        """
        current_time = utime.ticks_ms()
        self.pulse_count += 1
        self.pulse_times.append(current_time)
        # Keep only pulses within the sample window
        cutoff_time = current_time - self.sample_window_ms
        self.pulse_times = [t for t in self.pulse_times if t > cutoff_time]
    
    def read_speed(self):
        """Read speed from the hall sensor and return the value in km/h.
        
        Reads pulses from the GPIO pin (hall sensor measuring pedal speed/cadence)
        and calculates bike speed based on pedal speed, gear ratio, and wheel circumference.
        Works with both real GPIO pulses and simulated pulses for testing.
        
        If simulated RPM is enabled, pulses are continuously regenerated at the target RPM.
        
        Speed = pedal_speed * gear_ratio * wheel_circumference
        
        Returns:
            Speed reading in km/h.
        """
        # Process pulses (works for both real GPIO and simulated pulses)
        current_time = utime.ticks_ms()
        
        # If simulated RPM is enabled, regenerate pulses consistently at the target RPM
        if self.simulated_rpm_enabled:
            # Always regenerate pulses to maintain consistent RPM
            # This ensures the pulse pattern is always correct for the target RPM
            self.pulse_times = []
            self.pulse_count = 0
            self._initialize_default_pulses(self.target_rpm)
        else:
            # Clean up old pulse times (older than sample window) for real GPIO pulses
            cutoff_time = current_time - self.sample_window_ms
            self.pulse_times = [t for t in self.pulse_times if t > cutoff_time]
        
        if len(self.pulse_times) < 2:
            # Need at least 2 pulses to calculate pedal speed
            speed_kmh = 0.0
        else:
            # Calculate pedal speed (revolutions per second)
            time_span = self.pulse_times[-1] - self.pulse_times[0]
            if time_span > 0:
                time_span_seconds = time_span / 1000.0
                num_revolutions = len(self.pulse_times) - 1  # Number of pedal revolutions
                pedal_rps = num_revolutions / time_span_seconds  # Revolutions per second
                
                # Get current gear ratio
                if self.gear_selector is not None:
                    gear_ratio = self.gear_selector.get_current_ratio()
                else:
                    gear_ratio = 1.0  # Default to 1:1 if no gear selector
                
                # Calculate bike speed: pedal_rps * gear_ratio * wheel_circumference
                # Convert to km/h: (m/s) * 3.6
                # Apply calibration factor to adjust for actual wheel size/measurements
                wheel_speed_mps = pedal_rps * gear_ratio * self.wheel_circumference * self.calibration_factor
                speed_kmh = wheel_speed_mps * 3.6
            else:
                speed_kmh = 0.0
        
        self.last_read_speed = speed_kmh
        return speed_kmh
    
    def update_display(self, lcd, rgb_color_func, back_col):
        """Update the speed display on the LCD using the last read speed.
        
        Displays "Speed - kmph" or "Speed - mph" as a label at the top,
        with the speed value displayed below in larger text.
        If simulated RPM is enabled, also displays the current RPM value.
        
        Args:
            lcd: LCD display object to update.
            rgb_color_func: Function to convert RGB values to display color.
            back_col: Background color for the display area.
        """
        if self.last_read_speed is not None:
            # Convert to selected unit (speed is stored internally in km/h)
            if self.unit == 'mph':
                display_speed = self.last_read_speed * 0.621371  # Convert km/h to mph
                unit_label = "mph"
            else:
                display_speed = self.last_read_speed
                unit_label = "kmph"
            
            # Round to 1 decimal place
            rounded_speed = round(display_speed, 1)
            # Format with 1 decimal place
            speed_str = "{:.1f}".format(rounded_speed)
            
            # Clear display area (full width for centered speed, enough height for label and large speed value)
            # Always display CRPM, WRPM, load, and incline (4 lines)
            display_height = 205
            lcd.fill_rect(0, self.label_y, self.screen_width, display_height, back_col)
            
            # Display label at top: "Speed - kmph" or "Speed - mph" (size 3)
            # Ensure display positions are valid
            if self.display_x is None:
                self.display_x = 0
            if self.label_y is None:
                self.label_y = 0
            
            label_text = "Speed-" + unit_label
            try:
                label_color = rgb_color_func(255, 255, 255)
                if label_color is not None and self.display_x is not None and self.label_y is not None:
                    lcd.write_text(label_text, int(self.display_x), int(self.label_y), 3, int(label_color))
            except (TypeError, ValueError, AttributeError):
                # Skip label display if there's an error
                pass
            
            # Calculate center position for speed number
            # Base font is 8 pixels per character
            # Reduced font size to 8 (from 10) to accommodate decimal display
            # Ensure screen_width is valid
            if self.screen_width is None:
                self.screen_width = 240  # Default fallback
            if self.speed_y is None:
                self.speed_y = 30  # Default fallback
            
            char_width_base = 8
            # Use font size 7 to ensure "99.9" (4 characters) fits on 240px screen
            # 4 characters * 8px * 7 = 224px, which fits comfortably
            font_size = 7
            char_width = char_width_base * font_size
            speed_text_width = len(speed_str) * char_width
            
            # Ensure screen width is valid for centering calculation
            if self.screen_width is None:
                self.screen_width = 240
            
            # Calculate centered position, ensuring it doesn't go negative
            speed_x = max(0, (self.screen_width - speed_text_width) // 2)
            
            # Ensure all values are valid before calling write_text
            try:
                speed_color = rgb_color_func(255, 255, 255)
                if speed_color is not None and speed_x is not None and self.speed_y is not None:
                    # Display speed value below in larger text (size 7), centered, with 1 decimal place
                    # Font size stays consistent regardless of number length
                    lcd.write_text(speed_str, int(speed_x), int(self.speed_y), font_size, int(speed_color))
            except (TypeError, ValueError, AttributeError):
                # Skip speed display if there's an error
                pass
            
            # Always display CRPM, WRPM, load, and incline
            try:
                # Ensure speed_y is valid before calculating rpm_y
                if self.speed_y is None:
                    self.speed_y = 30
                
                # Calculate crank RPM from pulse data
                if len(self.pulse_times) >= 2:
                    time_span = self.pulse_times[-1] - self.pulse_times[0]
                    if time_span > 0:
                        time_span_seconds = time_span / 1000.0
                        num_revolutions = len(self.pulse_times) - 1
                        pedal_rps = num_revolutions / time_span_seconds
                        crank_rpm = int(pedal_rps * 60)  # Convert to RPM
                    else:
                        crank_rpm = 0
                elif self.simulated_rpm_enabled and self.target_rpm is not None:
                    # Use simulated RPM if available
                    crank_rpm = int(self.target_rpm)
                else:
                    crank_rpm = 0
                
                # Calculate wheel RPM from crank RPM and gear ratio
                if self.gear_selector is not None:
                    gear_ratio = self.gear_selector.get_current_ratio()
                    wheel_rpm = int(crank_rpm * gear_ratio)
                else:
                    gear_ratio = 1.0
                    wheel_rpm = crank_rpm
                
                # Display crank RPM
                crank_rpm_y = self.speed_y + 61  # Position below speed value (moved up half a line)
                crank_rpm_text = "CRPM: " + str(crank_rpm)
                
                # Display wheel RPM below crank RPM
                wheel_rpm_y = crank_rpm_y + 18  # Position below crank RPM (reduced spacing)
                wheel_rpm_text = "WRPM: " + str(wheel_rpm)
                
                # Center the RPM text
                char_width_base = 8  # Ensure it's defined
                rpm_char_width = char_width_base * 2  # Size 2 font (reduced from 3)
                
                if self.screen_width is None:
                    self.screen_width = 240
                
                # Center crank RPM text
                crank_rpm_text_width = len(crank_rpm_text) * rpm_char_width
                crank_rpm_x = (self.screen_width - crank_rpm_text_width) // 2
                
                # Center wheel RPM text
                wheel_rpm_text_width = len(wheel_rpm_text) * rpm_char_width
                wheel_rpm_x = (self.screen_width - wheel_rpm_text_width) // 2
                
                rpm_color = rgb_color_func(200, 200, 200)
                
                # Display crank RPM
                if rpm_color is not None and crank_rpm_x is not None and crank_rpm_y is not None:
                    lcd.write_text(crank_rpm_text, int(crank_rpm_x), int(crank_rpm_y), 2, int(rpm_color))
                
                # Display wheel RPM
                if rpm_color is not None and wheel_rpm_x is not None and wheel_rpm_y is not None:
                    lcd.write_text(wheel_rpm_text, int(wheel_rpm_x), int(wheel_rpm_y), 2, int(rpm_color))
                
                # Display load value if load controller is available
                if self.load_controller is not None:
                    try:
                        load_percent = self.load_controller.get_current_load_percent()
                        load_y = wheel_rpm_y + 18  # Position below wheel RPM (reduced spacing)
                        load_text = "Load: " + str(int(load_percent))  # Same format as RPM (integer, no decimal)
                        
                        # Center load text
                        load_text_width = len(load_text) * rpm_char_width
                        load_x = (self.screen_width - load_text_width) // 2
                        
                        if rpm_color is not None and load_x is not None and load_y is not None:
                            lcd.write_text(load_text, int(load_x), int(load_y), 2, int(rpm_color))
                        
                            # Display incline value
                            incline_percent = self.load_controller.get_incline()
                            incline_y = load_y + 18  # Position below load (reduced spacing)
                            # Format incline: positive = uphill, negative = downhill, 0 = flat
                            if incline_percent > 0:
                                incline_text = "Hill: +" + str(int(incline_percent))
                            elif incline_percent < 0:
                                incline_text = "Hill: " + str(int(incline_percent))  # Negative sign included
                            else:
                                incline_text = "Hill: 0"
                        
                        # Center incline text
                        incline_text_width = len(incline_text) * rpm_char_width
                        incline_x = (self.screen_width - incline_text_width) // 2
                        
                        if rpm_color is not None and incline_x is not None and incline_y is not None:
                            lcd.write_text(incline_text, int(incline_x), int(incline_y), 2, int(rpm_color))
                        
                    except (TypeError, ValueError, AttributeError):
                        # Skip load/incline display if there's an error
                        pass
            except (TypeError, ValueError, AttributeError):
                # Skip RPM display if there's an error
                pass
    
    def update_speed(self):
        """Check if speed needs to be updated (changed by 1 unit or more).
        
        Reads the current speed and checks if it has changed by at least
        1 unit (1 km/h or 1 mph) from the last displayed value.
        
        Returns:
            True if display should be updated, False otherwise.
        """
        speed_reading = self.read_speed()
        
        # Convert to display unit for comparison
        if self.unit == 'mph':
            display_speed = speed_reading * 0.621371
            last_displayed = self.last_displayed_speed * 0.621371 if self.last_displayed_speed is not None else None
        else:
            display_speed = speed_reading
            last_displayed = self.last_displayed_speed
        
        # Only update display if speed changed by 1 unit or more
        if last_displayed is None or abs(display_speed - last_displayed) >= 1.0:
            self.last_displayed_speed = speed_reading  # Store in km/h internally
            return True
        return False
    
    def toggle_unit(self):
        """Toggle between km/h and mph units.
        
        Returns:
            The new unit string ('kmph' or 'mph').
        """
        if self.unit == 'mph':
            self.unit = 'kmph'
        else:
            self.unit = 'mph'
        # Reset last displayed speed to force update on next call
        self.last_displayed_speed = None
        return self.unit
    
    def toggle_simulated_rpm(self):
        """Toggle simulated RPM on/off.
        
        When enabled, generates pulses at the target RPM.
        When disabled, clears simulated pulses (real GPIO pulses will still work).
        
        Returns:
            True if simulated RPM is now enabled, False if disabled.
        """
        self.simulated_rpm_enabled = not self.simulated_rpm_enabled
        
        if self.simulated_rpm_enabled:
            # Enable: generate pulses at target RPM
            self._initialize_default_pulses(self.target_rpm)
        else:
            # Disable: clear simulated pulses (keep real GPIO pulses if any)
            # Only clear if we're in mock mode (no GPIO pin) or if we want to clear all
            if self.gpio_pin is None:
                # Mock mode: clear all pulses
                self.pulse_times = []
                self.pulse_count = 0
            # If GPIO pin is set, real pulses will continue to work
        
        # Reset last displayed speed to force immediate update
        self.last_displayed_speed = None
        return self.simulated_rpm_enabled
    
    def set_calibration_from_wheel_rpm(self, known_speed_kmh, known_wheel_rpm):
        """Set calibration factor based on known speed and wheel RPM.
        
        This allows calibrating the speed calculation to match actual measurements.
        For example: at 30 mph (48.28 km/h) with 388 wheel RPM for a 26-inch wheel.
        
        Args:
            known_speed_kmh: Known speed in km/h (e.g., 48.28 for 30 mph).
            known_wheel_rpm: Known wheel RPM at that speed (e.g., 388).
        
        Formula: 
        - Wheel speed (m/s) = wheel_rps * circumference
        - Speed (km/h) = wheel_speed_mps * 3.6
        - Calibration adjusts circumference to match known values
        """
        if known_wheel_rpm > 0 and known_speed_kmh > 0:
            # Convert wheel RPM to revolutions per second
            wheel_rps = known_wheel_rpm / 60.0
            
            # Calculate what the circumference should be to match known speed
            # known_speed_kmh = wheel_rps * circumference * 3.6
            # circumference = known_speed_kmh / (wheel_rps * 3.6)
            calculated_circumference = known_speed_kmh / (wheel_rps * 3.6)
            
            # Calculate calibration factor to adjust from default circumference
            if self.wheel_circumference > 0:
                self.calibration_factor = calculated_circumference / self.wheel_circumference
            else:
                self.calibration_factor = 1.0
                self.wheel_circumference = calculated_circumference
        else:
            self.calibration_factor = 1.0
    
    def set_calibration_factor(self, factor):
        """Set calibration factor directly.
        
        Args:
            factor: Calibration factor (1.0 = no adjustment, >1.0 = increase speed, <1.0 = decrease speed).
        """
        self.calibration_factor = max(0.1, min(2.0, factor))  # Clamp between 0.1 and 2.0
    
    def set_wheel_circumference(self, circumference_meters):
        """Set the wheel circumference in meters.
        
        Args:
            circumference_meters: Wheel circumference in meters.
                                For a 26-inch wheel: ~2.075 meters
                                For a 700c wheel: ~2.1 meters
        """
        self.wheel_circumference = circumference_meters
    
    def adjust_rpm(self, rpm_delta):
        """Adjust the target RPM for simulated pulses.
        
        Only works if simulated RPM is enabled.
        
        Args:
            rpm_delta: Change in RPM (positive to increase, negative to decrease).
                      Typically ±10 RPM.
        
        This regenerates the pulse pattern to match the new target RPM.
        """
        if not self.simulated_rpm_enabled:
            return  # Don't adjust if simulated RPM is disabled
        
        # Update target RPM (clamp to reasonable range: 0-200 RPM)
        self.target_rpm = max(0, min(200, self.target_rpm + rpm_delta))
        
        # Clear existing pulses and regenerate with new RPM
        self.pulse_times = []
        self.pulse_count = 0
        self._initialize_default_pulses(self.target_rpm)
        
        # Reset last displayed speed to force immediate update
        self.last_displayed_speed = None
    
    def simulate_pulse(self, increment=True):
        """Simulate a GPIO pulse for testing purposes.
        
        This method mimics what the interrupt handler does when a real
        pulse is detected. It adds or removes a timestamp from the pulse_times list,
        which will be used by read_speed() to calculate speed.
        
        Args:
            increment: If True, adds a pulse (increment). If False, removes the most recent pulse (decrement).
        
        This allows testing the speed calculation logic without needing
        actual hardware pulses.
        """
        current_time = utime.ticks_ms()
        
        if increment:
            # Add a pulse (increment)
            self.pulse_count += 1
            self.pulse_times.append(current_time)
        else:
            # Remove the most recent pulse (decrement)
            if len(self.pulse_times) > 0:
                self.pulse_times.pop()
            if self.pulse_count > 0:
                self.pulse_count -= 1
        
        # Keep only pulses within the sample window
        cutoff_time = current_time - self.sample_window_ms
        self.pulse_times = [t for t in self.pulse_times if t > cutoff_time]
        # Reset last displayed speed to force immediate update
        self.last_displayed_speed = None

