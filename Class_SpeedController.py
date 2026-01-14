class SpeedController:
    """Speed controller class for managing speed calculations from RPM.

    This class handles all speed calculations and converts RPM to speed in mph.
    Display logic is handled by the View class.
    """

    def __init__(self, crank_sensor=None, wheel_speed_sensor=None, gear_selector=None,
                 load_controller=None, unit='mph'):
        """Initialize the speed controller.

        Args:
            crank_sensor: CrankSensor instance (default: None).
            wheel_speed_sensor: WheelSpeedSensor instance (default: None).
            gear_selector: GearSelector instance to get current gear ratio (default: None).
            load_controller: LoadController instance to get current load (default: None).
            unit: Speed unit to display - always 'mph' (default: 'mph').
        """
        self.crank_sensor = crank_sensor
        self.wheel_speed_sensor = wheel_speed_sensor
        self.gear_selector = gear_selector
        self.load_controller = load_controller
        self.unit = 'mph'  # Always use mph

        # Wheel circumference and calibration
        self.wheel_circumference = 2.075  # meters (26-inch wheel default)
        self.calibration_factor = 1.0  # Calibration factor to adjust speed calculation
        self.fixed_gear_adjustment = 6.2  # Fixed gear adjustment factor for wheel sensor RPM

    def get_crank_rpm(self):
        """Get current crank RPM from crank sensor.

        Returns:
            Crank RPM (revolutions per minute), or 0 if sensor not available.
        """
        if self.crank_sensor is not None:
            return self.crank_sensor.get_rpm()
        return 0

    def get_wheel_rpm(self):
        """Get current wheel RPM.

        If wheel speed sensor is available, returns direct measurement.
        Otherwise, calculates from crank RPM and gear ratio.

        Returns:
            Wheel RPM (revolutions per minute), or 0 if not available.
        """
        if self.wheel_speed_sensor is not None:
            # Direct measurement from wheel sensor
            return self.wheel_speed_sensor.get_rpm()
        elif self.crank_sensor is not None and self.gear_selector is not None:
            # Calculate from crank RPM and gear ratio
            crank_rpm = self.crank_sensor.get_rpm()
            gear_ratio = self.gear_selector.get_current_ratio()
            return int(crank_rpm * gear_ratio)
        return 0

    def rpm_to_speed_kmh(self, rpm):
        """Convert RPM to speed in km/h.

        Args:
            rpm: Revolutions per minute.

        Returns:
            Speed in km/h.
        """
        # Speed (km/h) = RPM * circumference (m) * 0.06
        # Formula: RPM revolutions/min * circumference (m) * 60 min/hour / 1000 m/km = RPM * circumference * 0.06
        return rpm * self.wheel_circumference * self.calibration_factor * 0.06

    def rpm_to_speed_mph(self, rpm):
        """Convert RPM to speed in mph.

        Args:
            rpm: Revolutions per minute.

        Returns:
            Speed in mph.
        """
        speed_kmh = self.rpm_to_speed_kmh(rpm)
        return speed_kmh * 0.621371  # Convert km/h to mph

    def get_crank_speed(self):
        """Get current crank speed in mph.

        Returns:
            Speed in mph.
        """
        crank_rpm = self.get_crank_rpm()
        if self.unit == 'mph':
            return self.rpm_to_speed_mph(crank_rpm)
        else:
            return self.rpm_to_speed_kmh(crank_rpm)

    def get_wheel_speed(self):
        """Get current wheel speed in mph.

        Returns:
            Speed in mph.
        """
        wheel_rpm = self.get_wheel_rpm()
        if self.unit == 'mph':
            return self.rpm_to_speed_mph(wheel_rpm)
        else:
            return self.rpm_to_speed_kmh(wheel_rpm)

    def get_calculated_speed(self):
        """Get calculated speed: wheel RPM divided by fixed_gear_adjustment, then multiplied by gear ratio.

        This is the main speed display - (wheel speed sensor / fixed_gear_adjustment) * virtual gear ratio.

        Returns:
            Speed in mph.
        """
        if self.wheel_speed_sensor is not None:
            # Get wheel RPM from sensor
            wheel_rpm = self.wheel_speed_sensor.get_rpm()

            # Protect against division by zero
            if self.fixed_gear_adjustment <= 0:
                # Use safe default if adjustment is invalid
                self.fixed_gear_adjustment = 1.0

            # Divide by fixed_gear_adjustment before applying gear ratio
            adjusted_wheel_rpm = wheel_rpm / self.fixed_gear_adjustment

            # Multiply by gear ratio to get virtual speed
            if self.gear_selector is not None:
                gear_ratio = self.gear_selector.get_current_ratio()
                virtual_rpm = adjusted_wheel_rpm * gear_ratio
            else:
                virtual_rpm = adjusted_wheel_rpm

            # Convert to speed
            if self.unit == 'mph':
                return self.rpm_to_speed_mph(virtual_rpm)
            else:
                return self.rpm_to_speed_kmh(virtual_rpm)

        # Fallback to wheel speed if no wheel sensor
        return self.get_wheel_speed()

    def set_wheel_circumference(self, circumference_meters):
        """Set the wheel circumference in meters.

        Args:
            circumference_meters: Wheel circumference in meters.
                                For a 26-inch wheel: ~2.075 meters
                                For a 700c wheel: ~2.1 meters
        """
        # Input validation
        if not isinstance(circumference_meters, (int, float)):
            print(f"Warning: Invalid circumference_meters type: {type(circumference_meters)}. Using default 2.075")
            circumference_meters = 2.075

        if circumference_meters <= 0:
            print(f"Warning: circumference_meters must be > 0. Got {circumference_meters}. Using default 2.075")
            circumference_meters = 2.075

        self.wheel_circumference = float(circumference_meters)

    def set_calibration_from_wheel_rpm(self, known_speed_kmh, known_wheel_rpm):
        """Set calibration factor based on known speed and wheel RPM.

        Args:
            known_speed_kmh: Known speed in km/h.
            known_wheel_rpm: Known wheel RPM at that speed.
        """
        # Input validation
        if not isinstance(known_speed_kmh, (int, float)) or not isinstance(known_wheel_rpm, (int, float)):
            print(f"Warning: Invalid calibration parameters. Types: speed={type(known_speed_kmh)}, rpm={type(known_wheel_rpm)}")
            self.calibration_factor = 1.0
            return

        if known_wheel_rpm > 0 and known_speed_kmh > 0:
            # Convert wheel RPM to revolutions per second
            wheel_rps = known_wheel_rpm / 60.0

            # Calculate what the circumference should be to match known speed
            calculated_circumference = known_speed_kmh / (wheel_rps * 3.6)

            # Calculate calibration factor to adjust from default circumference
            if self.wheel_circumference > 0:
                self.calibration_factor = calculated_circumference / self.wheel_circumference
            else:
                self.calibration_factor = 1.0
                self.wheel_circumference = calculated_circumference
        else:
            self.calibration_factor = 1.0

    def set_fixed_gear_adjustment(self, adjustment_value):
        """Set the fixed gear adjustment factor.

        This value is used to divide wheel sensor RPM before applying virtual gear ratios.
        Default is 6.2.

        Args:
            adjustment_value: The fixed gear adjustment factor (default: 6.2).
                            Must be greater than 0.
        """
        if adjustment_value > 0:
            self.fixed_gear_adjustment = adjustment_value
        else:
            print("Warning: fixed_gear_adjustment must be greater than 0. Keeping current value.")


