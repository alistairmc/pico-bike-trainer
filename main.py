# WaceShare Library code
# Alistair Mcgranaghan 24/09/2022
from machine import Pin,SPI,PWM
import machine
import framebuf
import utime
import os
import math
from Class_LCD1Inch3 import LCD1Inch3 as LCD_Driver_Class
from Class_CrankSensor import CrankSensor
from Class_WheelSpeedSensor import WheelSpeedSensor
from Class_SpeedController import SpeedController
from Class_GearSelector import GearSelector
from Class_LoadController import LoadController
from Class_MotorSensor import MotorSensor
from Class_ColorHelper import ColorHelper
from Class_View import View
from Class_ButtonController import ButtonController

# Global values
LCD = LCD_Driver_Class()
gear_selector = GearSelector(num_gears=7, min_ratio=1.0, max_ratio=4.5)
motor_sensor = MotorSensor(motor_count_gpio_pin=0, motor_stop_gpio_pin=1)  # Motor RPM sensor on GPIO pin 0, Motor stop trigger on GPIO pin 1
load_controller = LoadController(l298n_in1_pin=5, l298n_in2_pin=6, gear_selector=gear_selector, motor_sensor=motor_sensor, lcd=LCD, rgb_color_func=ColorHelper.rgb_color)  # L298N motor control pins

# Perform startup calibration: move to bottom position, then to top position (180 degrees)
load_controller.startup_calibration()

# Crank sensor (measures pedal/crank speed - returns RPM only)
crank_sensor = CrankSensor(gpio_pin=7)

# Wheel speed sensor (measures flywheel/wheel speed directly - returns RPM only)
wheel_speed_sensor = WheelSpeedSensor(gpio_pin=4)

# Speed controller (manages all speed calculations)
speed_controller = SpeedController(
    crank_sensor=crank_sensor,
    wheel_speed_sensor=wheel_speed_sensor,
    gear_selector=gear_selector,
    load_controller=load_controller
)
speed_controller.set_wheel_circumference(2.075)  # 26-inch wheel circumference in meters
speed_controller.set_calibration_from_wheel_rpm(48.28, 388)  # 30 mph at 388 wheel RPM

# Initialize view (handles all display logic - MVC pattern)
# View class centralizes all display rendering, separating presentation from business logic
back_col = 0
view = View(LCD, ColorHelper.rgb_color, back_col, 
            speed_controller=speed_controller,
            gear_selector=gear_selector,
            load_controller=load_controller,
            screen_width=LCD.width,
            screen_height=LCD.height)

# Initialize button controller (handles all button inputs - MVC pattern)
button_controller = ButtonController(
    speed_controller=speed_controller,
    load_controller=load_controller,
    gear_selector=gear_selector,
    view=view,
    incline_step=5.0,
    max_incline=100.0,
    min_incline=-100.0
)

pwm = PWM(Pin(LCD.BL)) # Screen Brightness
pwm.freq(1000)
pwm.duty_u16(65535) # Full brightness

# =========== Main ============

# Background color - black
LCD.fill(ColorHelper.rgb_color(0,0,0))
# Apply initial load based on starting gear
load_controller.apply_load()
# Initial display of all components
view.render_all()

LCD.show()

# Display update timing - update 4 times per second (every 250ms)
display_update_interval_ms = 250
last_display_update_time = utime.ticks_ms()

# =========== Main loop ===============
while True:
    # Check all buttons and handle actions
    # ButtonController handles all button logic, debouncing, and action dispatching
    button_controller.check_buttons()
    
    # Continuously update load to adjust motor position towards target
    # This ensures the motor moves to the correct position based on gear and incline
    load_controller.apply_load()
    
    # Update display 4 times per second (every 250ms)
    # View class handles all display rendering (MVC pattern)
    current_time = utime.ticks_ms()
    if utime.ticks_diff(current_time, last_display_update_time) >= display_update_interval_ms:
        # Redraw all displays using View class
        view.render_all()
        last_display_update_time = current_time

    utime.sleep_us(200)  # Small delay to prevent tight loop





