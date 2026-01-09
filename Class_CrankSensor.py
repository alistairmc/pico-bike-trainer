from machine import Pin
import utime


class CrankSensor:
    """Crank sensor class for reading crank/pedal RPM.
    
    This class handles hall sensor-based crank speed readings.
    One pulse = one full crank rotation (360 degrees).
    Returns RPM only - speed calculations are handled by SpeedController.
    """
    
    def __init__(self, gpio_pin):
        """Initialize the crank sensor.
        
        Args:
            gpio_pin: GPIO pin number for the hall sensor.
        """
        self.gpio_pin = gpio_pin
        # Initialize pulse tracking
        self.pulse_count = 0
        self.last_pulse_time = 0
        self.pulse_times = []  # Store recent pulse times for RPM calculation
        self.crpm_pulse_times = []  # Store extended pulse times for CRPM calculation (10 second window)
        self.sample_window_ms = 5000  # 5 second window for RPM calculation
        self.crpm_sample_window_ms = 10000  # 10 second window for CRPM calculation (allows low RPM detection)
        
        self.hall_sensor = Pin(gpio_pin, Pin.IN, Pin.PULL_UP)
        # Note: GPIO reads pedal speed (cadence), not wheel speed
        # Sensor is normally OFF (LOW) and goes HIGH when triggered
        # Set up interrupt handler for pulse counting (trigger on rising edge)
        self.hall_sensor.irq(trigger=Pin.IRQ_RISING, handler=self._pulse_handler)
    
    def _pulse_handler(self, _pin):
        """Interrupt handler for hall sensor pulses.
        
        One pulse = one full crank rotation (360 degrees).
        Sensor is normally LOW and goes HIGH when triggered.
        
        Args:
            _pin: The pin that triggered the interrupt (unused but required by MicroPython).
        """
        current_time = utime.ticks_ms()
        self.pulse_count += 1
        self.last_pulse_time = current_time
        self.pulse_times.append(current_time)
        self.crpm_pulse_times.append(current_time)  # Also add to extended window for CRPM
        # Keep only pulses within the sample window (for speed calculation)
        cutoff_time = current_time - self.sample_window_ms
        self.pulse_times = [t for t in self.pulse_times if t > cutoff_time]
        # Keep pulses within CRPM sample window (longer window for low RPM detection)
        crpm_cutoff_time = current_time - self.crpm_sample_window_ms
        self.crpm_pulse_times = [t for t in self.crpm_pulse_times if t > crpm_cutoff_time]
    
    def _calculate_crank_rpm(self):
        """Calculate current crank RPM from pulse data.
        
        Returns:
            Crank RPM (revolutions per minute), or 0 if not enough data.
        """
        current_time = utime.ticks_ms()
        
        # Clean up old pulses from CRPM window
        crpm_cutoff_time = current_time - self.crpm_sample_window_ms
        self.crpm_pulse_times = [t for t in self.crpm_pulse_times if t > crpm_cutoff_time]
        
        if len(self.crpm_pulse_times) >= 2:
            # Multiple pulses: calculate RPM from time span
            time_span = self.crpm_pulse_times[-1] - self.crpm_pulse_times[0]
            if time_span > 0:
                time_span_seconds = time_span / 1000.0
                num_revolutions = len(self.crpm_pulse_times) - 1
                pedal_rps = num_revolutions / time_span_seconds
                return int(pedal_rps * 60)
        elif len(self.crpm_pulse_times) == 1:
            # Single pulse: calculate RPM from time since that pulse
            time_since_pulse = utime.ticks_diff(current_time, self.crpm_pulse_times[0])
            if time_since_pulse > 0 and time_since_pulse < 15000:  # Within 15 seconds
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
        """Get current crank RPM.
        
        Processes pulses and returns the current crank RPM.
        
        Returns:
            Crank RPM (revolutions per minute).
        """
        # Clean up old pulse times (older than sample window)
        current_time = utime.ticks_ms()
        cutoff_time = current_time - self.sample_window_ms
        self.pulse_times = [t for t in self.pulse_times if t > cutoff_time]
        
        # Calculate and return current crank RPM
        return self._calculate_crank_rpm()

