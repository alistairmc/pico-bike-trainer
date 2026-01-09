from machine import Pin
import utime


class ButtonController:
    """Button controller class for managing all button inputs and actions.
    
    This class handles all button reading, debouncing, and action dispatching.
    Separates input handling from business logic (MVC pattern).
    """
    
    def __init__(self, speed_controller=None, load_controller=None,
                 gear_selector=None, view=None, incline_step=5.0, max_incline=100.0, 
                 min_incline=-100.0, debounce_ms=200):
        """Initialize the button controller.
        
        Args:
            speed_controller: SpeedController instance (default: None).
            load_controller: LoadController instance (default: None).
            gear_selector: GearSelector instance (default: None).
            view: View instance for display updates (default: None).
            incline_step: Incline change per button press in percent (default: 5.0).
            max_incline: Maximum incline percentage (default: 100.0).
            min_incline: Minimum incline percentage (default: -100.0).
            debounce_ms: Debounce delay in milliseconds (default: 200).
        """
        self.speed_controller = speed_controller
        self.load_controller = load_controller
        self.gear_selector = gear_selector
        self.view = view
        self.incline_step = incline_step
        self.max_incline = max_incline
        self.min_incline = min_incline
        self.debounce_ms = debounce_ms
        
        # Initialize button pins
        self.toggle_unit_button = Pin(16, Pin.IN, Pin.PULL_UP)  # Toggle speed unit (kmph/mph)
        
        self.increase_incline_button = Pin(14, Pin.IN, Pin.PULL_UP)  # Increase incline (uphill)
        self.decrease_incline_button = Pin(18, Pin.IN, Pin.PULL_UP)  # Decrease incline (downhill)
        self.decrement_gear_button = Pin(3, Pin.IN, Pin.PULL_UP)  # Decrement gear
        self.increment_gear_button = Pin(2, Pin.IN, Pin.PULL_UP)  # Increment gear
        self.control_button = Pin(20, Pin.IN, Pin.PULL_UP)  # Control button (currently unused)
        
        # Track previous button states for release detection
        self.prev_toggle_unit = 1
        self.prev_increase_incline = 1
        self.prev_decrease_incline = 1
        self.prev_decrement_gear = 1
        self.prev_increment_gear = 1
        self.prev_control = 1
        
    def check_buttons(self):
        """Check all buttons and perform associated actions.
        
        This method should be called in the main loop to continuously check for button releases.
        Detects button release (transition from pressed to released) and triggers actions.
        Handles debouncing and triggers appropriate actions.
        """
        # Get current button states
        toggle_unit_state = self.toggle_unit_button.value()
        increase_incline_state = self.increase_incline_button.value()
        decrease_incline_state = self.decrease_incline_button.value()
        decrement_gear_state = self.decrement_gear_button.value()
        increment_gear_state = self.increment_gear_button.value()
        control_state = self.control_button.value()
        
        # Toggle speed unit (detect release: was pressed, now released)
        if self.prev_toggle_unit == 0 and toggle_unit_state == 1:
            if self.speed_controller is not None:
                self.speed_controller.toggle_unit()
                self._force_display_update()
            utime.sleep_ms(self.debounce_ms)
        self.prev_toggle_unit = toggle_unit_state
        
        # Increase incline (uphill) - detect release
        if self.prev_increase_incline == 0 and increase_incline_state == 1:
            if self.load_controller is not None:
                current_incline = self.load_controller.get_incline()
                new_incline = min(current_incline + self.incline_step, self.max_incline)
                self.load_controller.set_incline(new_incline)
                self._force_display_update()
            utime.sleep_ms(self.debounce_ms)
        self.prev_increase_incline = increase_incline_state
        
        # Decrease incline (downhill) - detect release
        if self.prev_decrease_incline == 0 and decrease_incline_state == 1:
            if self.load_controller is not None:
                current_incline = self.load_controller.get_incline()
                new_incline = max(current_incline - self.incline_step, self.min_incline)
                self.load_controller.set_incline(new_incline)
                self._force_display_update()
            utime.sleep_ms(self.debounce_ms)
        self.prev_decrease_incline = decrease_incline_state
        
        # Decrement gear - detect release
        if self.prev_decrement_gear == 0 and decrement_gear_state == 1:
            if self.gear_selector is not None:
                if self.gear_selector.decrement_gear():
                    # Update display immediately to show new gear (don't wait for motor)
                    self._force_display_update()
                    # Then update load based on new gear (motor moves in background)
                    if self.load_controller is not None:
                        self.load_controller.apply_load()
            utime.sleep_ms(self.debounce_ms)
        self.prev_decrement_gear = decrement_gear_state
        
        # Increment gear - detect release
        if self.prev_increment_gear == 0 and increment_gear_state == 1:
            if self.gear_selector is not None:
                if self.gear_selector.increment_gear():
                    # Update display immediately to show new gear (don't wait for motor)
                    self._force_display_update()
                    # Then update load based on new gear (motor moves in background)
                    if self.load_controller is not None:
                        self.load_controller.apply_load()
            utime.sleep_ms(self.debounce_ms)
        self.prev_increment_gear = increment_gear_state
        
        # Control button (currently unused)
        self.prev_control = control_state
    
    def _force_display_update(self):
        """Force an immediate display update.
        
        Used when button actions require immediate visual feedback.
        """
        if self.view is not None:
            self.view.render_all()

