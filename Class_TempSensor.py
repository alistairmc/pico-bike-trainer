from machine import ADC


class TempSensor:
    """Temperature sensor class for reading and displaying temperature.
    
    This class handles ADC-based temperature sensor readings and provides
    methods to read temperature values and update the display.
    """
    
    def __init__(self, adc_pin=4, screen_width=240, screen_height=240, display_x=None, display_y=None):
        """Initialize the temperature sensor.
        
        Args:
            adc_pin: ADC pin number for the temperature sensor (default: 4).
            screen_width: Width of the display screen in pixels (default: 240).
            screen_height: Height of the display screen in pixels (default: 240).
            display_x: X coordinate for temperature display (default: 0).
            display_y: Y coordinate for temperature display (default: screen_height - 30).
        """
        self.temp_sensor = ADC(adc_pin)
        self.temp_conversion_factor = 3.3 / 65535
        self.last_displayed_temp = None  # Track last displayed temperature
        self.last_read_temp = None  # Track last read temperature
        self.screen_width = screen_width
        self.screen_height = screen_height
        # Set display position (default to bottom-left if not specified)
        self.display_x = display_x if display_x is not None else 0
        self.display_y = display_y if display_y is not None else screen_height - 30
    
    def read_temp(self):
        """Read temperature from the sensor and return the value in Celsius.
        
        Returns:
            Temperature reading in degrees Celsius.
        """
        temp_reading = 27 - ((self.temp_sensor.read_u16() * self.temp_conversion_factor) - 0.706) / 0.001721
        self.last_read_temp = temp_reading
        return temp_reading
    
    def update_display(self, lcd, rgb_color_func, back_col):
        """Update the temperature display on the LCD using the last read temperature.
        
        Temperature is rounded to the nearest full degree and displayed
        with 0 decimal place.
        
        Args:
            lcd: LCD display object to update.
            rgb_color_func: Function to convert RGB values to display color.
            back_col: Background color for the display area.
        """
        if self.last_read_temp is not None:
            # Round to nearest full degree
            rounded_temp = round(self.last_read_temp)
            # Format with 0 decimal place
            temp_str = str(rounded_temp)
            # Clear area around text (approximate text area: 50 pixels wide, 30 pixels tall)
            lcd.fill_rect(self.display_x, self.display_y - 10, 50, 30, back_col)
            lcd.write_text("Temp:" + temp_str + "C", self.display_x, self.display_y, 3, rgb_color_func(255, 255, 255))
    
    def update_temp(self):
        """Check if temperature needs to be updated (changed by 0.5 degrees or more).
        
        Reads the current temperature and checks if it has changed by at least
        0.5 degrees Celsius from the last displayed value.
        
        Returns:
            True if display should be updated, False otherwise.
        """
        temp_reading = self.read_temp()
        
        # Only update display if temperature changed by 0.5 degrees or more
        if self.last_displayed_temp is None or abs(temp_reading - self.last_displayed_temp) >= 0.5:
            self.last_displayed_temp = temp_reading
            return True
        return False

