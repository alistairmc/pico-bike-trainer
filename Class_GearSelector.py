class GearSelector:
    """Gear selector class for managing bike gear selection.

    This class handles gear selection logic and gear ratio calculations.
    Display rendering is handled by the View class.
    """

    def __init__(self, num_gears, min_ratio, max_ratio):
        """Initialize the gear selector.

        Args:
            num_gears: Number of gears available (e.g., 8 for an 8-speed cassette).
            min_ratio: Minimum gear ratio (gear 1, easiest to pedal).
            max_ratio: Maximum gear ratio (highest gear, hardest to pedal).
        """
        self.num_gears = num_gears
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.current_gear = 1  # Start at gear 1 (easiest)

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


