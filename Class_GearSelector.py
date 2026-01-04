class GearSelector:
    """Gear selector class for displaying and managing bike gears.
    
    This class handles gear selection display along the bottom of the screen,
    with the selected gear highlighted with a white box and inverted text.
    """
    
    def __init__(self, num_gears, min_ratio, max_ratio, screen_width=240, screen_height=240, display_y=None):
        """Initialize the gear selector.
        
        Args:
            num_gears: Number of gears available (e.g., 8 for an 8-speed cassette).
            min_ratio: Minimum gear ratio (gear 1, easiest to pedal).
            max_ratio: Maximum gear ratio (highest gear, hardest to pedal).
            screen_width: Width of the display screen in pixels (default: 240).
            screen_height: Height of the display screen in pixels (default: 240).
            display_y: Y coordinate for gear display (default: screen_height - 20).
        """
        self.num_gears = num_gears
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.current_gear = 1  # Start at gear 1 (easiest)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.display_y = display_y if display_y is not None else screen_height - 20
        
        # Calculate gear ratios (linearly distributed from min to max)
        # Gear 1 = min_ratio (easiest), Gear num_gears = max_ratio (hardest)
        self.gear_ratios = {}
        if num_gears == 1:
            self.gear_ratios[1] = min_ratio
        else:
            ratio_step = (max_ratio - min_ratio) / (num_gears - 1)
            for gear_num in range(1, num_gears + 1):
                self.gear_ratios[gear_num] = min_ratio + (ratio_step * (gear_num - 1))
        
        # Calculate gear box dimensions and spacing
        self.gear_box_width = 25
        self.gear_box_height = 20
        self.gear_spacing = 5
        self.total_width = (self.num_gears * self.gear_box_width) + ((self.num_gears - 1) * self.gear_spacing)
        self.start_x = (self.screen_width - self.total_width) // 2  # Center the gear display
    
    def increment_gear(self):
        """Increment to the next gear.
        
        Returns:
            True if gear was changed, False if already at maximum.
        """
        if self.current_gear < self.num_gears:
            self.current_gear += 1
            return True
        return False
    
    def decrement_gear(self):
        """Decrement to the previous gear.
        
        Returns:
            True if gear was changed, False if already at minimum.
        """
        if self.current_gear > 1:
            self.current_gear -= 1
            return True
        return False
    
    def get_current_ratio(self):
        """Get the gear ratio for the currently selected gear.
        
        Returns:
            The gear ratio for the current gear.
        """
        return self.gear_ratios.get(self.current_gear, self.min_ratio)
    
    def get_gear_ratio(self, gear_num):
        """Get the gear ratio for a specific gear.
        
        Args:
            gear_num: The gear number (1 to num_gears).
        
        Returns:
            The gear ratio for the specified gear, or min_ratio if invalid.
        """
        return self.gear_ratios.get(gear_num, self.min_ratio)
    
    def update_display(self, lcd, rgb_color_func, back_col):
        """Update the gear display on the LCD.
        
        Displays all gears along the bottom, with the selected gear
        highlighted with a white box and inverted text.
        
        Args:
            lcd: LCD display object to update.
            rgb_color_func: Function to convert RGB values to display color.
            back_col: Background color for the display area.
        """
        # Clear the gear display area
        lcd.fill_rect(0, self.display_y - 2, self.screen_width, self.gear_box_height + 4, back_col)
        
        # Display each gear
        for gear_num in range(1, self.num_gears + 1):
            x_pos = self.start_x + ((gear_num - 1) * (self.gear_box_width + self.gear_spacing))
            
            if gear_num == self.current_gear:
                # Selected gear: white box with inverted text (black text)
                # Draw white box
                lcd.fill_rect(x_pos, self.display_y, self.gear_box_width, self.gear_box_height, rgb_color_func(255, 255, 255))
                # Draw gear number in black (inverted)
                gear_str = str(gear_num)
                # Center the text in the box (size 2 = 8*2 = 16 pixels per character)
                text_width = 16 * len(gear_str)
                text_x = x_pos + (self.gear_box_width - text_width) // 2
                lcd.write_text(gear_str, text_x, self.display_y + 6, 2, rgb_color_func(0, 0, 0))
            else:
                # Unselected gear: normal text on background
                gear_str = str(gear_num)
                # Center the text in the box (size 2 = 8*2 = 16 pixels per character)
                text_width = 16 * len(gear_str)
                text_x = x_pos + (self.gear_box_width - text_width) // 2
                lcd.write_text(gear_str, text_x, self.display_y + 6, 2, rgb_color_func(255, 255, 255))

