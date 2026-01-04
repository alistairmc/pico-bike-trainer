from machine import Pin
import utime


class LoadController:
    """Load controller class for applying resistance using a stepper motor.
    
    This class controls a stepper motor to move magnets closer/farther from
    the wheel to apply resistance, simulating both gear-based resistance
    (lower gears easier, higher gears harder) and incline/decline resistance.
    """
    
    def __init__(self, step_pin, dir_pin, enable_pin=None, gear_selector=None, base_load_factor=1.0, max_steps=200):
        """Initialize the load controller.
        
        Args:
            step_pin: GPIO pin number for STEP signal to stepper driver.
            dir_pin: GPIO pin number for DIR (direction) signal to stepper driver.
            enable_pin: GPIO pin number for ENABLE signal (optional, default: None).
            gear_selector: GearSelector instance to get current gear ratio (default: None).
            base_load_factor: Base load multiplier for gear resistance (default: 1.0).
            max_steps: Maximum number of steps (magnet position range, default: 200).
        """
        self.step_pin = Pin(step_pin, Pin.OUT)
        self.dir_pin = Pin(dir_pin, Pin.OUT)
        self.enable_pin = Pin(enable_pin, Pin.OUT) if enable_pin is not None else None
        
        # Enable motor if enable pin is provided (active low on most drivers)
        if self.enable_pin is not None:
            self.enable_pin.value(0)  # Enable motor (0 = enabled, 1 = disabled)
        
        self.gear_selector = gear_selector
        self.base_load_factor = base_load_factor
        self.max_steps = max_steps
        self.current_position = 0  # Current stepper position (0 = magnets farthest, max_steps = closest)
        
        self.incline_percent = 0.0  # Current incline/decline (-100 to +100)
        self.step_delay_us = 1000  # Delay between steps in microseconds
        
        # Move to initial position (zero load)
        self._move_to_position(0)
    
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
        
        On a flat road, lower gears (lower ratios) should be easier,
        higher gears (higher ratios) should be harder.
        Base load is centered around 0.5 (middle of range) to allow
        incline/decline to add/subtract from this center point.
        
        Returns:
            Base load value based on gear ratio (0.25 to 0.75, centered at 0.5).
        """
        if self.gear_selector is not None:
            current_ratio = self.gear_selector.get_current_ratio()
            min_ratio = self.gear_selector.min_ratio
            max_ratio = self.gear_selector.max_ratio
            
            # Normalize ratio to 0-1 range
            if max_ratio > min_ratio:
                normalized_ratio = (current_ratio - min_ratio) / (max_ratio - min_ratio)
            else:
                normalized_ratio = 0.5
            
            # Map normalized ratio to 0.25-0.75 range (centered around 0.5)
            # This gives room for incline to add/subtract ±0.25
            base_load = 0.25 + (normalized_ratio * 0.5)
            
            return base_load * self.base_load_factor
        else:
            # No gear selector, use middle of range (0.5)
            return 0.5 * self.base_load_factor
    
    def _calculate_incline_load(self):
        """Calculate load contribution from incline/decline.
        
        Returns:
            Incline load value (-0.25 to +0.25).
            This allows incline to adjust ±25% from the centered base load.
        """
        # Incline adds resistance, decline reduces it
        # Convert percentage to load factor (-0.25 to +0.25)
        # This gives ±25% adjustment range from the centered base load
        return (self.incline_percent / 100.0) * 0.25
    
    def _step_motor(self, steps, direction):
        """Move the stepper motor a specified number of steps.
        
        Args:
            steps: Number of steps to move.
            direction: Direction (True = forward/closer, False = backward/farther).
        """
        if steps == 0:
            return
        
        # Set direction
        self.dir_pin.value(1 if direction else 0)
        utime.sleep_us(10)  # Small delay for direction to settle
        
        # Step the motor
        for _ in range(steps):
            self.step_pin.value(1)
            utime.sleep_us(self.step_delay_us)
            self.step_pin.value(0)
            utime.sleep_us(self.step_delay_us)
    
    def _move_to_position(self, target_position):
        """Move stepper motor to a specific position.
        
        Args:
            target_position: Target position (0 to max_steps).
        """
        target_position = max(0, min(self.max_steps, int(target_position)))
        steps_to_move = target_position - self.current_position
        
        if steps_to_move != 0:
            direction = steps_to_move > 0
            self._step_motor(abs(steps_to_move), direction)
            self.current_position = target_position
    
    def _update_load(self):
        """Update the stepper motor position based on current gear and incline.
        
        Total load = base_load (from gear) + incline_load
        Higher load = magnets closer to wheel = higher position value
        """
        base_load = self._calculate_base_load()
        incline_load = self._calculate_incline_load()
        
        # Combine loads (base load is always positive, incline can be negative)
        total_load = base_load + incline_load
        
        # Clamp to 0-1 range
        total_load = max(0.0, min(1.0, total_load))
        
        # Convert load to stepper position (0 = no load, max_steps = max load)
        target_position = int(total_load * self.max_steps)
        
        # Move stepper to target position
        self._move_to_position(target_position)
    
    def apply_load(self):
        """Apply the calculated load based on current gear and incline.
        
        This should be called whenever the gear changes or incline is updated.
        Moves the stepper motor to position magnets at the correct distance.
        """
        self._update_load()
    
    def remove_load(self):
        """Remove all load (set to zero).
        
        Moves magnets to farthest position, effectively removing all resistance.
        """
        self._move_to_position(0)
    
    def set_load(self, load_percent):
        """Set the load directly as a percentage.
        
        Args:
            load_percent: Load percentage (0.0 to 1.0).
        """
        load_percent = max(0.0, min(1.0, float(load_percent)))
        target_position = int(load_percent * self.max_steps)
        self._move_to_position(target_position)
    
    def get_current_load_percent(self):
        """Return the current load as a percentage (0.0 to 100.0).
        
        Returns:
            Current load percentage based on stepper position.
        """
        if self.max_steps > 0:
            return (self.current_position / self.max_steps) * 100.0
        return 0.0

