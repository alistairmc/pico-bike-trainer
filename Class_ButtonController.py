from machine import Pin
import utime


class ButtonController:
    """Button controller class for managing all button inputs and actions.
    
    This class handles all button reading, debouncing, and action dispatching.
    Separates input handling from business logic (MVC pattern).
    """
    
    def __init__(self, speed_controller=None, load_controller=None,
                 gear_selector=None, timer_controller=None, view=None, 
                 incline_step=5.0, max_incline=100.0, min_incline=-100.0, 
                 debounce_ms=200, gear_click_timeout_ms=800):
        """Initialize the button controller.
        
        Args:
            speed_controller: SpeedController instance (default: None).
            load_controller: LoadController instance (default: None).
            gear_selector: GearSelector instance (default: None).
            timer_controller: TimerController instance (default: None).
            view: View instance for display updates (default: None).
            incline_step: Incline change per button press in percent (default: 5.0).
            max_incline: Maximum incline percentage (default: 100.0).
            min_incline: Minimum incline percentage (default: -100.0).
            debounce_ms: Debounce delay in milliseconds for most buttons (default: 200).
            gear_click_timeout_ms: Timeout in milliseconds after last click before applying gear changes (default: 800).
                                    Allows for slower, more deliberate clicking while still being responsive.
        """
        self.speed_controller = speed_controller
        self.load_controller = load_controller
        self.gear_selector = gear_selector
        self.timer_controller = timer_controller
        self.view = view
        self.incline_step = incline_step
        self.max_incline = max_incline
        self.min_incline = min_incline
        self.debounce_ms = debounce_ms
        self.gear_click_timeout_ms = gear_click_timeout_ms
        
        # Multi-click tracking for gear buttons
        self.increment_click_count = 0
        self.decrement_click_count = 0
        self.increment_last_click_time = 0
        self.decrement_last_click_time = 0
        self.increment_start_gear = None
        self.decrement_start_gear = None
        
        # Initialize button pins
        self.increase_incline_button = Pin(16, Pin.IN, Pin.PULL_UP)  # Increase incline (uphill)
        self.decrease_incline_button = Pin(17, Pin.IN, Pin.PULL_UP)  # Decrease incline (downhill)
        self.decrement_gear_button = Pin(3, Pin.IN, Pin.PULL_UP)  # Decrement gear
        self.increment_gear_button = Pin(2, Pin.IN, Pin.PULL_UP)  # Increment gear
        self.control_button = Pin(18, Pin.IN, Pin.PULL_UP)  # Control button (currently unused)
        
        # Track previous button states for release detection
        self.prev_increase_incline = 1
        self.prev_decrease_incline = 1
        self.prev_decrement_gear = 1
        self.prev_increment_gear = 1
        self.prev_control = 1
        
        # Timestamp-based debouncing (more efficient than sleep)
        self.last_button_action_time = {}  # Track last action time per button
        
        # Control button tracking for long press detection
        self.control_button_press_time = 0  # When control button was pressed (for long press detection)
        self.control_button_held = False  # Track if control button is currently held
        
    def check_buttons(self):
        """Check all buttons and perform associated actions.
        
        This method should be called in the main loop to continuously check for button releases.
        Detects button release (transition from pressed to released) and triggers actions.
        Uses timestamp-based debouncing to avoid blocking the main loop.
        """
        current_time = utime.ticks_ms()
        
        # Get current button states (check all buttons first to avoid missing rapid presses)
        increase_incline_state = self.increase_incline_button.value()
        decrease_incline_state = self.decrease_incline_button.value()
        decrement_gear_state = self.decrement_gear_button.value()
        increment_gear_state = self.increment_gear_button.value()
        control_state = self.control_button.value()
        
        # Increase incline (uphill) - detect release
        if self.prev_increase_incline == 0 and increase_incline_state == 1:
            last_action = self.last_button_action_time.get('increase_incline', 0)
            if utime.ticks_diff(current_time, last_action) >= self.debounce_ms:
                if self.load_controller is not None:
                    current_incline = self.load_controller.get_incline()
                    new_incline = min(current_incline + self.incline_step, self.max_incline)
                    self.load_controller.set_incline(new_incline)
                    self._force_display_update()
                self.last_button_action_time['increase_incline'] = current_time
        self.prev_increase_incline = increase_incline_state
        
        # Decrease incline (downhill) - detect release
        if self.prev_decrease_incline == 0 and decrease_incline_state == 1:
            last_action = self.last_button_action_time.get('decrease_incline', 0)
            if utime.ticks_diff(current_time, last_action) >= self.debounce_ms:
                if self.load_controller is not None:
                    current_incline = self.load_controller.get_incline()
                    new_incline = max(current_incline - self.incline_step, self.min_incline)
                    self.load_controller.set_incline(new_incline)
                    self._force_display_update()
                self.last_button_action_time['decrease_incline'] = current_time
        self.prev_decrease_incline = decrease_incline_state
        
        # Handle gear button multi-click counting and timeout
        self._process_gear_clicks(current_time)
        
        # Decrement gear - detect release and count clicks
        if self.prev_decrement_gear == 0 and decrement_gear_state == 1:
            if self.gear_selector is not None:
                # Cancel any pending increment clicks when decrement is clicked
                if self.increment_click_count > 0:
                    print(f"Cancelled {self.increment_click_count} increment clicks")
                    self.increment_click_count = 0
                    self.increment_start_gear = None
                
                # Start tracking if this is the first click
                if self.decrement_click_count == 0:
                    self.decrement_start_gear = self.gear_selector.current_gear
                # Increment click count
                self.decrement_click_count += 1
                self.decrement_last_click_time = current_time
                print(f"Gear decrement click #{self.decrement_click_count} (will apply after {self.gear_click_timeout_ms}ms delay)")
        self.prev_decrement_gear = decrement_gear_state
        
        # Increment gear - detect release and count clicks
        if self.prev_increment_gear == 0 and increment_gear_state == 1:
            if self.gear_selector is not None:
                # Cancel any pending decrement clicks when increment is clicked
                if self.decrement_click_count > 0:
                    print(f"Cancelled {self.decrement_click_count} decrement clicks")
                    self.decrement_click_count = 0
                    self.decrement_start_gear = None
                
                # Start tracking if this is the first click
                if self.increment_click_count == 0:
                    self.increment_start_gear = self.gear_selector.current_gear
                # Increment click count
                self.increment_click_count += 1
                self.increment_last_click_time = current_time
                print(f"Gear increment click #{self.increment_click_count} (will apply after {self.gear_click_timeout_ms}ms delay)")
        self.prev_increment_gear = increment_gear_state
        
        # Control button - Timer control
        if self.timer_controller is not None:
            # Detect button press (transition from released to pressed)
            if self.prev_control == 1 and control_state == 0:
                self.control_button_press_time = current_time
                self.control_button_held = True
            
            # Detect button release (transition from pressed to released)
            if self.prev_control == 0 and control_state == 1:
                self.control_button_held = False
                hold_duration = utime.ticks_diff(current_time, self.control_button_press_time)
                
                # Check for long press (3 seconds = 3000ms) while paused
                if hold_duration >= 3000 and self.timer_controller.get_state() == 'paused':
                    # Reset timer
                    self.timer_controller.reset()
                    self._force_display_update()
                # Check for short press (normal click)
                elif hold_duration < 3000:
                    # Debounce check
                    last_action = self.last_button_action_time.get('control', 0)
                    if utime.ticks_diff(current_time, last_action) >= self.debounce_ms:
                        self._handle_timer_toggle(current_time)
                        self.last_button_action_time['control'] = current_time
            
            # Check for long press while button is still held (for reset when paused)
            if self.control_button_held and control_state == 0:
                hold_duration = utime.ticks_diff(current_time, self.control_button_press_time)
                if hold_duration >= 3000 and self.timer_controller.get_state() == 'paused':
                    # Reset timer immediately when 3 seconds reached
                    self.timer_controller.reset()
                    self.control_button_held = False
                    print("Timer reset (long press)")
                    self._force_display_update()
        
        self.prev_control = control_state
    
    def _process_gear_clicks(self, current_time):
        """Process accumulated gear clicks and apply gear changes after timeout.
        
        Counts rapid clicks and jumps directly to target gear after user stops clicking.
        
        Args:
            current_time: Current time in milliseconds.
        """
        if self.gear_selector is None:
            return
        
        # Process decrement clicks
        if self.decrement_click_count > 0:
            if self.decrement_start_gear is None:
                # Shouldn't happen, but reset if it does
                print(f"ERROR: decrement_click_count={self.decrement_click_count} but start_gear is None, resetting")
                self.decrement_click_count = 0
                return
            
            time_since_last = utime.ticks_diff(current_time, self.decrement_last_click_time)
            if time_since_last >= self.gear_click_timeout_ms:
                # Timeout expired - apply all gear changes at once
                current_gear = self.gear_selector.current_gear
                target_gear = max(1, self.decrement_start_gear - self.decrement_click_count)
                
                print(f"Decrement timeout: start={self.decrement_start_gear}, clicks={self.decrement_click_count}, current={current_gear}, target={target_gear}")
                
                # Jump directly to target gear
                if target_gear != current_gear:
                    self.gear_selector.current_gear = target_gear
                    print(f"Gear jumped: {self.decrement_start_gear} -> {target_gear} ({self.decrement_click_count} clicks)")
                    
                    # Update display and load
                    self._force_display_update()
                    if self.load_controller is not None:
                        self.load_controller.apply_load(force=True)
                else:
                    print(f"Gear already at target {target_gear}, no change needed")
                
                # Reset click tracking
                self.decrement_click_count = 0
                self.decrement_start_gear = None
        
        # Process increment clicks
        if self.increment_click_count > 0 and self.increment_start_gear is not None:
            time_since_last = utime.ticks_diff(current_time, self.increment_last_click_time)
            if time_since_last >= self.gear_click_timeout_ms:
                # Timeout expired - apply all gear changes at once
                if self.gear_selector is not None:
                    max_gear = self.gear_selector.num_gears
                    target_gear = min(max_gear, self.increment_start_gear + self.increment_click_count)
                    current_gear = self.gear_selector.current_gear
                    
                    # Jump directly to target gear
                    if target_gear != current_gear:
                        self.gear_selector.current_gear = target_gear
                        print(f"Gear jumped: {self.increment_start_gear} -> {target_gear} ({self.increment_click_count} clicks)")
                        
                        # Update display and load
                        self._force_display_update()
                        if self.load_controller is not None:
                            self.load_controller.apply_load(force=True)
                
                # Reset click tracking
                self.increment_click_count = 0
                self.increment_start_gear = None
    
    def _handle_timer_toggle(self, current_time):
        """Handle timer start/pause/resume toggle.
        
        Args:
            current_time: Current time in milliseconds.
        """
        if self.timer_controller is None:
            return
        
        timer_state = self.timer_controller.get_state()
        
        if timer_state == 'stopped':
            # Start timer
            self.timer_controller.start(current_time)
        elif timer_state == 'running':
            # Pause timer
            self.timer_controller.pause(current_time)
        elif timer_state == 'paused':
            # Resume timer
            self.timer_controller.start(current_time)
        
        self._force_display_update()
    
    def _force_display_update(self):
        """Force an immediate display update.
        
        Used when button actions require immediate visual feedback.
        """
        if self.view is not None:
            self.view.render_all()

