class View:
    """View class for managing all display logic and rendering.

    This class handles all display operations, separating presentation
    from business logic. Controllers and sensors provide data, View renders it.
    """

    def __init__(self, lcd, rgb_color_func, back_col, speed_controller=None, 
                 gear_selector=None, load_controller=None, screen_width=240, screen_height=240):
        """Initialize the view.

        Args:
            lcd: LCD display object.
            rgb_color_func: Function to convert RGB values to display color.
            back_col: Background color for the display.
            speed_controller: SpeedController instance (default: None).
            gear_selector: GearSelector instance (default: None).
            load_controller: LoadController instance (default: None).
            screen_width: Width of the display screen in pixels (default: 240).
            screen_height: Height of the display screen in pixels (default: 240).
        """
        self.lcd = lcd
        self.rgb_color_func = rgb_color_func
        self.back_col = back_col
        self.speed_controller = speed_controller
        self.gear_selector = gear_selector
        self.load_controller = load_controller
        self.screen_width = screen_width
        self.screen_height = screen_height

    def render_all(self):
        """Render all display elements.

        This is the main method to update the entire display.
        Errors are caught and logged to prevent display failures from crashing the system.
        """
        try:
            # Clear screen
            self.lcd.fill(self.back_col)

            # Render speed information
            if self.speed_controller is not None:
                try:
                    self._render_speed()
                except Exception as e:
                    print(f"Error rendering speed: {e}")
                    # Try to show error on display
                    try:
                        error_color = self.rgb_color_func(255, 0, 0)
                        if error_color is not None:
                            self.lcd.write_text("Speed Error", 50, 50, 2, int(error_color))
                    except:
                        pass

            # Render gear selector
            if self.gear_selector is not None:
                try:
                    self._render_gear_selector()
                except Exception as e:
                    print(f"Error rendering gear selector: {e}")

            # Show the display
            self.lcd.show()
        except Exception as e:
            print(f"Critical error in render_all: {e}")
            # Try to show error message
            try:
                self.lcd.fill(0)
                error_color = self.rgb_color_func(255, 0, 0)
                if error_color is not None:
                    self.lcd.write_text("Display Error", 30, 100, 2, int(error_color))
                self.lcd.show()
            except:
                pass

    def _render_speed(self):
        """Render speed information (calculated speed from wheel * gear ratio, RPM, load, incline)."""
        if self.speed_controller is None:
            return

        # Get calculated speed (wheel RPM * gear ratio)
        calculated_speed = self.speed_controller.get_calculated_speed()
        wheel_rpm = self.speed_controller.get_wheel_rpm()

        # Unit label
        unit_label = "mph" if self.speed_controller.unit == 'mph' else "kmph"

        # Clear display area
        display_height = 205
        self.lcd.fill_rect(0, 0, self.screen_width, display_height, self.back_col)

        # Display speed label
        label_y = 0
        speed_y = 50

        label_text = "Speed-" + unit_label
        try:
            label_color = self.rgb_color_func(255, 255, 255)
            if label_color is not None:
                self.lcd.write_text(label_text, 0, label_y, 3, int(label_color))
        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error rendering speed label: {e}")
            # Continue rendering other elements

        # Format speed value
        speed_str = "{:.1f}".format(round(calculated_speed, 1))
        char_width_base = 8
        font_size = 7
        char_width = char_width_base * font_size
        speed_text_width = len(speed_str) * char_width
        speed_x = max(0, (self.screen_width - speed_text_width) // 2)

        try:
            speed_color = self.rgb_color_func(255, 255, 255)
            if speed_color is not None:
                self.lcd.write_text(speed_str, int(speed_x), speed_y, font_size, int(speed_color))
        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error rendering speed value: {e}")
            # Continue rendering other elements

        # Display wheel RPM, load, and incline
        try:
            rpm_y = speed_y + 61
            rpm_char_width = char_width_base * 2  # Size 2 font

            # Display wheel RPM
            wheel_rpm_text = "WRPM: " + str(wheel_rpm)
            wheel_rpm_text_width = len(wheel_rpm_text) * rpm_char_width
            wheel_rpm_x = (self.screen_width - wheel_rpm_text_width) // 2

            rpm_color = self.rgb_color_func(200, 200, 200)
            if rpm_color is not None:
                self.lcd.write_text(wheel_rpm_text, int(wheel_rpm_x), int(rpm_y), 2, int(rpm_color))

            # Display Road load value if load controller is available
            if self.load_controller is not None:
                try:
                    load_percent = self.load_controller.get_current_load_percent()
                    load_y = rpm_y + 18
                    load_text = "Road Load: " + str(int(load_percent))

                    load_text_width = len(load_text) * rpm_char_width
                    load_x = (self.screen_width - load_text_width) // 2

                    if rpm_color is not None:
                        self.lcd.write_text(load_text, int(load_x), int(load_y), 2, int(rpm_color))

                    # Display incline value
                    incline_percent = self.load_controller.get_incline()
                    incline_y = load_y + 18
                    if incline_percent > 0:
                        incline_text = "Hill: +" + str(int(incline_percent))
                    elif incline_percent < 0:
                        incline_text = "Hill: " + str(int(incline_percent))
                    else:
                        incline_text = "Hill: 0"

                    incline_text_width = len(incline_text) * rpm_char_width
                    incline_x = (self.screen_width - incline_text_width) // 2

                    if rpm_color is not None:
                        self.lcd.write_text(incline_text, int(incline_x), int(incline_y), 2, int(rpm_color))
                except (TypeError, ValueError, AttributeError) as e:
                    print(f"Error rendering load/incline: {e}")
                    # Continue rendering other elements
        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error rendering RPM/load section: {e}")
            # Continue rendering other elements

    def _render_gear_selector(self):
        """Render gear selector display."""
        if self.gear_selector is None:
            return

        # Calculate display position (bottom of screen)
        display_y = self.screen_height - 20
        # Calculate starting x position to center the gear display
        start_x = (self.screen_width - self.gear_selector.total_width) // 2

        # Clear the gear display area
        self.lcd.fill_rect(0, display_y - 2, 
                          self.screen_width, self.gear_selector.gear_box_height + 4, self.back_col)

        # Display each gear
        for gear_num in range(1, self.gear_selector.num_gears + 1):
            x_pos = start_x + ((gear_num - 1) * 
                              (self.gear_selector.gear_box_width + self.gear_selector.gear_spacing))

            if gear_num == self.gear_selector.current_gear:
                # Selected gear: white box with inverted text (black text)
                # Draw white box
                self.lcd.fill_rect(x_pos, display_y, 
                                  self.gear_selector.gear_box_width, self.gear_selector.gear_box_height, 
                                  self.rgb_color_func(255, 255, 255))
                # Draw gear number in black (inverted)
                gear_str = str(gear_num)
                # Center the text in the box (size 2 = 8*2 = 16 pixels per character)
                text_width = 16 * len(gear_str)
                text_x = x_pos + (self.gear_selector.gear_box_width - text_width) // 2
                self.lcd.write_text(gear_str, text_x, display_y + 6, 2, 
                                   self.rgb_color_func(0, 0, 0))
            else:
                # Unselected gear: normal text on background
                gear_str = str(gear_num)
                # Center the text in the box (size 2 = 8*2 = 16 pixels per character)
                text_width = 16 * len(gear_str)
                text_x = x_pos + (self.gear_selector.gear_box_width - text_width) // 2
                self.lcd.write_text(gear_str, text_x, display_y + 6, 2, 
                                   self.rgb_color_func(255, 255, 255))

    def display_calibration_status(self, status_text, detail_text=None):
        """Display calibration status on the screen.

        Args:
            status_text: Main status message to display.
            detail_text: Optional detail message to display below main status.
        """
        # Clear the entire screen
        self.lcd.fill(self.back_col)

        # Calculate text positions (centered)
        text_color = self.rgb_color_func(255, 255, 255)  # White text
        title_color = self.rgb_color_func(255, 200, 0)  # Yellow/orange for title

        # Title
        title = "CALIBRATION"
        title_size = 3
        title_char_width = 8 * title_size
        title_width = len(title) * title_char_width
        title_x = max(0, (self.screen_width - title_width) // 2)
        title_y = 20

        try:
            if title_color is not None:
                self.lcd.write_text(title, int(title_x), title_y, title_size, int(title_color))
        except (TypeError, ValueError, AttributeError):
            pass

        # Main status text
        status_size = 2
        status_char_width = 8 * status_size
        status_width = len(status_text) * status_char_width
        status_x = max(0, (self.screen_width - status_width) // 2)
        status_y = 80

        try:
            if text_color is not None:
                self.lcd.write_text(status_text, int(status_x), status_y, status_size, int(text_color))
        except (TypeError, ValueError, AttributeError):
            pass

        # Detail text (if provided)
        if detail_text:
            detail_size = 2
            detail_char_width = 8 * detail_size
            detail_width = len(detail_text) * detail_char_width
            detail_x = max(0, (self.screen_width - detail_width) // 2)
            detail_y = 120

            try:
                if text_color is not None:
                    self.lcd.write_text(detail_text, int(detail_x), detail_y, detail_size, int(text_color))
            except (TypeError, ValueError, AttributeError):
                pass

        # Show the display
        self.lcd.show()

