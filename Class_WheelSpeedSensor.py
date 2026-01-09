from machine import Pin
import utime


class WheelSpeedSensor:
    """Wheel speed sensor class for reading flywheel/wheel RPM.
    
    This class handles hall sensor-based wheel speed readings from the flywheel.
    One pulse = one full wheel revolution (360 degrees).
    Returns RPM only - speed calculations are handled by SpeedController.
    """
    
    def __init__(self, gpio_pin):
        """Initialize the wheel speed sensor.
        
        Args:
            gpio_pin: GPIO pin number for the hall sensor.
        """
        self.gpio_pin = gpio_pin
        # Initialize pulse tracking
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.pulse_times = []  # Store recent pulse times for RPM calculation
        self.sample_window_ms = 5000  # 5 second window for RPM calculation
        
        self.hall_sensor = Pin(gpio_pin, Pin.IN, Pin.PULL_UP)
        # Sensor is normally OFF (LOW) and goes HIGH when triggered
        # Set up interrupt handler for pulse counting (trigger on rising edge)
        self.hall_sensor.irq(trigger=Pin.IRQ_RISING, handler=self._pulse_handler)
    
    def _pulse_handler(self, _pin):
        """Interrupt handler for hall sensor pulses.
        
        One pulse = one full wheel revolution (360 degrees).
        Sensor is normally LOW and goes HIGH when triggered.
        
        Args:
            _pin: The pin that triggered the interrupt (unused but required by MicroPython).
        """
        current_time = utime.ticks_ms()
        self.pulse_count += 1
        self.last_pulse_time = current_time
        self.pulse_times.append(current_time)
        # Keep only pulses within the sample window
        cutoff_time = current_time - self.sample_window_ms
        self.pulse_times = [t for t in self.pulse_times if t > cutoff_time]
    
    def _calculate_wheel_rpm(self):
        """Calculate current wheel RPM from pulse data.
        
        Returns:
            Wheel RPM (revolutions per minute), or 0 if not enough data.
        """
        current_time = utime.ticks_ms()
        
        # Clean up old pulses
        cutoff_time = current_time - self.sample_window_ms
        self.pulse_times = [t for t in self.pulse_times if t > cutoff_time]
        
        if len(self.pulse_times) >= 2:
            # Multiple pulses: calculate RPM from time span
            time_span = self.pulse_times[-1] - self.pulse_times[0]
            if time_span > 0:
                time_span_seconds = time_span / 1000.0
                num_revolutions = len(self.pulse_times) - 1
                wheel_rps = num_revolutions / time_span_seconds
                return int(wheel_rps * 60)
        elif len(self.pulse_times) == 1:
            # Single pulse: calculate RPM from time since that pulse
            time_since_pulse = utime.ticks_diff(current_time, self.pulse_times[0])
            if time_since_pulse > 0 and time_since_pulse < 5000:  # Within 5 seconds
                time_per_rev_seconds = time_since_pulse / 1000.0
                return int(60.0 / time_per_rev_seconds)
        elif self.last_pulse_time > 0:
            # No recent pulses, but we have a last pulse time
            time_since_pulse = utime.ticks_diff(current_time, self.last_pulse_time)
            if time_since_pulse > 0 and time_since_pulse < 5000:  # Within 5 seconds
                time_per_rev_seconds = time_since_pulse / 1000.0
                return int(60.0 / time_per_rev_seconds)
        
        return 0
    
    def get_rpm(self):
        """Get current wheel RPM.
        
        Processes pulses and returns the current wheel RPM.
        
        Returns:
            Wheel RPM (revolutions per minute).
        """
        # Clean up old pulse times
        current_time = utime.ticks_ms()
        cutoff_time = current_time - self.sample_window_ms
        self.pulse_times = [t for t in self.pulse_times if t > cutoff_time]
        
        # Calculate and return current wheel RPM
        return self._calculate_wheel_rpm()

