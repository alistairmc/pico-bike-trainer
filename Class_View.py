import utime

# RGB565 color constants
COLOR_BLACK = 0x0000
COLOR_WHITE = 0xFFFF
COLOR_RED = 0xF800
COLOR_GREEN = 0x07E0
COLOR_BLUE = 0x001F
COLOR_YELLOW = 0xFFE0
COLOR_ORANGE = 0xFDA0  # Yellow-orange
COLOR_GRAY = 0xC618  # Medium gray (200,200,200)


class View:
    """View class for managing all display logic and rendering.

    This class handles all display operations, separating presentation
    from business logic. Controllers and sensors provide data, View renders it.
    """

    def __init__(self, lcd, back_col, speed_controller=None,
                 gear_selector=None, load_controller=None, timer_controller=None,
                 ble_controller=None, screen_width=240, screen_height=240):
        """Initialize the view.

        Args:
            lcd: LCD display object.
            back_col: Background color for the display (RGB565 format).
            speed_controller: SpeedController instance (default: None).
            gear_selector: GearSelector instance (default: None).
            load_controller: LoadController instance (default: None).
            timer_controller: TimerController instance for timer display (default: None).
            ble_controller: BLEController instance for pairing status display (default: None).
            screen_width: Width of the display screen in pixels (default: 240).
            screen_height: Height of the display screen in pixels (default: 240).
        """
        self.lcd = lcd
        self.back_col = back_col
        self.speed_controller = speed_controller
        self.gear_selector = gear_selector
        self.load_controller = load_controller
        self.timer_controller = timer_controller
        self.ble_controller = ble_controller
        
        # Ensure screen dimensions are valid integers
        if screen_width is None:
            screen_width = 240
        if screen_height is None:
            screen_height = 240
        self.screen_width = int(screen_width)
        self.screen_height = int(screen_height)

    def render_all(self):
        """Render all display elements.

        This is the main method to update the entire display.
        Errors are caught and logged to prevent display failures from crashing the system.
        """
        try:
            # Check if in pairing mode - if so, only show pairing status
            if self.ble_controller is not None and self.ble_controller.is_pairing_mode():
                try:
                    self._render_pairing_status()
                    # Show the display and return early - don't render other elements
                    self.lcd.show()
                    return
                except Exception as e:
                    print(f"Error rendering pairing status: {e}")

            # Normal rendering (not in pairing mode)
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
                        self.lcd.write_text("Speed Error", 50, 50, 2, COLOR_RED)
                    except:
                        pass

            # Render timer (only when not in pairing mode)
            if self.timer_controller is not None:
                try:
                    self._render_timer()
                except Exception as e:
                    print(f"Error rendering timer: {e}")

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
                self.lcd.write_text("Display Error", 30, 100, 2, COLOR_RED)
                self.lcd.show()
            except:
                pass

    def _render_speed(self):
        """Render speed information (calculated speed from wheel * gear ratio, RPM, load, incline)."""
        if self.speed_controller is None:
            return

        # Get calculated speed (wheel RPM * gear ratio)
        calculated_speed = self.speed_controller.get_calculated_speed()
        # wheel_rpm = self.speed_controller.get_wheel_rpm()  # Not currently used (commented out display)

        # Validate calculated_speed
        if calculated_speed is None:
            calculated_speed = 0.0

        # Unit label (always mph)
        unit_label = "mph"

        # Clear display area
        display_height = 205
        self.lcd.fill_rect(0, 0, self.screen_width, display_height, self.back_col)

        # Display speed label
        label_y = 0
        speed_y = 50

        label_text = "Speed-" + unit_label
        try:
            self.lcd.write_text(label_text, 0, label_y, 3, COLOR_WHITE)
        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error rendering speed label: {e}")
            # Continue rendering other elements

        # Format speed value
        try:
            speed_str = "{:.1f}".format(round(calculated_speed, 1))
        except (TypeError, ValueError):
            speed_str = "0.0"
        char_width_base = 8
        font_size = 7
        char_width = char_width_base * font_size
        speed_text_width = len(speed_str) * char_width
        speed_x = max(0, (self.screen_width - speed_text_width) // 2)

        try:
            self.lcd.write_text(speed_str, int(speed_x), speed_y, font_size, COLOR_WHITE)
        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error rendering speed value: {e}")
            # Continue rendering other elements

        # Display wheel RPM, load, and incline
        try:
            rpm_y = speed_y + 61
            rpm_char_width = char_width_base * 2  # Size 2 font

            # Display wheel RPM - COMMENTED OUT
            # wheel_rpm_text = "WRPM: " + str(wheel_rpm)
            # wheel_rpm_text_width = len(wheel_rpm_text) * rpm_char_width
            # wheel_rpm_x = (self.screen_width - wheel_rpm_text_width) // 2

            # rpm_color = COLOR_GRAY
            # self.lcd.write_text(wheel_rpm_text, int(wheel_rpm_x), int(rpm_y), 2, rpm_color)

            # Display Road load value if load controller is available - COMMENTED OUT
            if self.load_controller is not None:
                try:
                    # load_percent = self.load_controller.get_current_load_percent()
                    # load_y = rpm_y + 18
                    # load_text = "Road Load: " + str(int(load_percent))

                    # load_text_width = len(load_text) * rpm_char_width
                    # load_x = (self.screen_width - load_text_width) // 2

                    # if rpm_color is not None:
                    #     self.lcd.write_text(load_text, int(load_x), int(load_y), 2, int(rpm_color))

                    # Display incline value
                    incline_percent = self.load_controller.get_incline()
                    # Validate incline_percent
                    if incline_percent is None:
                        incline_percent = 0.0
                    
                    incline_y = rpm_y + 18  # Changed from load_y + 18 since load is commented out
                    try:
                        if incline_percent > 0:
                            incline_text = "Hill: +" + str(int(incline_percent))
                        elif incline_percent < 0:
                            incline_text = "Hill: " + str(int(incline_percent))
                        else:
                            incline_text = "Hill: 0"
                    except (TypeError, ValueError):
                        incline_text = "Hill: 0"

                    incline_text_width = len(incline_text) * rpm_char_width
                    incline_x = (self.screen_width - incline_text_width) // 2

                    self.lcd.write_text(incline_text, int(incline_x), int(incline_y), 2, COLOR_GRAY)
                except (TypeError, ValueError, AttributeError) as e:
                    print(f"Error rendering load/incline: {e}")
                    # Continue rendering other elements
        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error rendering RPM/load section: {e}")
            # Continue rendering other elements

    def _render_timer(self):
        """Render timer display."""
        if self.timer_controller is None:
            return

        current_time = utime.ticks_ms()
        elapsed_ms = self.timer_controller.get_elapsed_ms(current_time)

        # Format timer as MM:SS
        total_seconds = elapsed_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        timer_text = f"{minutes:02d}:{seconds:02d}"

        # Display timer label and value
        try:
            timer_label = "Time:"
            timer_label_size = 2
            timer_value_size = 2

            char_width_base = 8
            label_char_width = char_width_base * timer_label_size
            value_char_width = char_width_base * timer_value_size

            # Position timer just above gear display
            # Gear display is at bottom (screen_height - 20)
            # Timer should be above it with a small gap
            gear_display_y = self.screen_height - 20  # Same calculation as gear selector
            timer_text_height = timer_value_size * 8  # Size 2 = 16 pixels tall
            gap = 6  # Gap between timer and gear display
            timer_y = gear_display_y - timer_text_height - gap

            # Calculate total width needed
            label_width = len(timer_label) * label_char_width
            value_width = len(timer_text) * value_char_width
            total_width = label_width + 4 + value_width  # 4px gap between label and value

            # Center the timer horizontally (like gear display)
            label_x = (self.screen_width - total_width) // 2
            label_y = timer_y

            # Calculate timer value position (next to label)
            timer_value_x = label_x + label_width + 4  # Small gap after label
            timer_value_y = label_y

            # Display label
            self.lcd.write_text(timer_label, label_x, label_y, timer_label_size, COLOR_GRAY)
            # Display timer value
            self.lcd.write_text(timer_text, int(timer_value_x), timer_value_y, timer_value_size, COLOR_GRAY)
        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error rendering timer: {e}")

    def _render_pairing_status(self):
        """Render BLE pairing status display."""
        if self.ble_controller is None:
            return

        try:
            # Clear screen before rendering pairing status
            self.lcd.fill(self.back_col)

            # Calculate remaining time
            current_time = utime.ticks_ms()
            pairing_start = self.ble_controller.get_pairing_mode_start_time()
            pairing_duration = self.ble_controller.get_pairing_mode_duration_ms()

            # Validate pairing_start before using it
            if pairing_start is None or pairing_start == 0:
                print("Warning: pairing_start is invalid, using current time")
                pairing_start = current_time

            elapsed = utime.ticks_diff(current_time, pairing_start)
            if elapsed is None:
                print("Warning: elapsed time calculation failed")
                elapsed = 0

            remaining_ms = max(0, pairing_duration - elapsed)
            remaining_sec = remaining_ms // 1000

            # Display pairing status prominently
            title = "BLE PAIRING"
            status_text = f"Time: {remaining_sec:3d}s"

            # Check if connected
            if self.ble_controller.is_connected():
                status_text = "CONNECTED!"
                status_color = COLOR_GREEN
            else:
                status_color = COLOR_ORANGE  # Yellow/Orange

            title_color = COLOR_WHITE

            # Calculate positions (centered)
            char_width_base = 8
            title_size = 3
            status_size = 2

            title_char_width = char_width_base * title_size
            status_char_width = char_width_base * status_size

            title_width = len(title) * title_char_width
            status_width = len(status_text) * status_char_width

            title_x = (self.screen_width - title_width) // 2
            title_y = 60  # Below speed display

            status_x = (self.screen_width - status_width) // 2
            status_y = title_y + (title_size * 8) + 10  # Below title

            # Draw title
            try:
                self.lcd.write_text(title, title_x, title_y, title_size, title_color)
            except (TypeError, ValueError, AttributeError) as e:
                print(f"Error rendering pairing title: {e}")

            # Draw status
            try:
                self.lcd.write_text(status_text, status_x, status_y, status_size, status_color)
            except (TypeError, ValueError, AttributeError) as e:
                print(f"Error rendering pairing status: {e}")

            # Draw connection status
            if not self.ble_controller.is_connected():
                instruction = "Waiting..."
                inst_size = 2
                inst_char_width = char_width_base * inst_size
                inst_width = len(instruction) * inst_char_width
                inst_x = (self.screen_width - inst_width) // 2
                inst_y = status_y + (status_size * 8) + 8

                try:
                    self.lcd.write_text(instruction, inst_x, inst_y, inst_size, COLOR_GRAY)
                except (TypeError, ValueError, AttributeError) as e:
                    print(f"Error rendering pairing instruction: {e}")

        except (TypeError, ValueError, AttributeError) as e:
            print(f"Error rendering pairing status: {e}")

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
                                  COLOR_WHITE)
                # Draw gear number in black (inverted)
                gear_str = str(gear_num)
                # Center the text in the box (size 2 = 8*2 = 16 pixels per character)
                text_width = 16 * len(gear_str)
                text_x = x_pos + (self.gear_selector.gear_box_width - text_width) // 2
                self.lcd.write_text(gear_str, text_x, display_y + 6, 2, COLOR_BLACK)
            else:
                # Unselected gear: normal text on background
                gear_str = str(gear_num)
                # Center the text in the box (size 2 = 8*2 = 16 pixels per character)
                text_width = 16 * len(gear_str)
                text_x = x_pos + (self.gear_selector.gear_box_width - text_width) // 2
                self.lcd.write_text(gear_str, text_x, display_y + 6, 2, COLOR_WHITE)

    def display_calibration_status(self, status_text, detail_text=None):
        """Display calibration status on the screen.

        Args:
            status_text: Main status message to display.
            detail_text: Optional detail message to display below main status.
        """
        # Clear the entire screen
        self.lcd.fill(self.back_col)

        # Calculate text positions (centered)
        text_color = COLOR_WHITE  # White text
        title_color = COLOR_ORANGE  # Yellow/orange for title

        # Title
        title = "CALIBRATION"
        title_size = 3
        title_char_width = 8 * title_size
        title_width = len(title) * title_char_width
        title_x = max(0, (self.screen_width - title_width) // 2)
        title_y = 20

        try:
            self.lcd.write_text(title, int(title_x), title_y, title_size, title_color)
        except (TypeError, ValueError, AttributeError):
            pass

        # Main status text
        status_size = 2
        status_char_width = 8 * status_size
        status_width = len(status_text) * status_char_width
        status_x = max(0, (self.screen_width - status_width) // 2)
        status_y = 80

        try:
            self.lcd.write_text(status_text, int(status_x), status_y, status_size, text_color)
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
                self.lcd.write_text(detail_text, int(detail_x), detail_y, detail_size, text_color)
            except (TypeError, ValueError, AttributeError):
                pass

        # Show the display
        self.lcd.show()

