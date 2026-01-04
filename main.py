# WaceShare Library code
# Alistair Mcgranaghan 24/09/2022
from machine import Pin,SPI,PWM,ADC
import machine
import framebuf
import utime
import os
import math
from Class_LCD1Inch3 import LCD1Inch3 as LCD_Driver_Class
from Class_TempSensor import TempSensor
from Class_SpeedSensor import SpeedSensor
from Class_GearSelector import GearSelector
from Class_LoadController import LoadController
from Class_MotorSensor import MotorSensor
from Class_ColorHelper import ColorHelper

# Global values
LCD = LCD_Driver_Class()
temp_sensor = TempSensor(screen_width=LCD.width, screen_height=LCD.height)
gear_selector = GearSelector(num_gears=7, min_ratio=1.0, max_ratio=4.5, screen_width=LCD.width, screen_height=LCD.height)
load_controller = LoadController(step_pin=5, dir_pin=6, enable_pin=7, gear_selector=gear_selector)  # Stepper motor control pins
motor_sensor = MotorSensor(motor_count_gpio_pin=0, motor_stop_gpio_pin=1, screen_width=LCD.width, screen_height=LCD.height)  # Motor RPM sensor on GPIO pin 0, Motor stop trigger on GPIO pin 1
speed_sensor = SpeedSensor(gpio_pin=1, gear_selector=gear_selector, load_controller=load_controller, screen_width=LCD.width, screen_height=LCD.height)
# Calibrate for 26-inch wheel: 30 mph (48.28 km/h) at 388 wheel RPM
# Note: This assumes the hall sensor measures wheel RPM, not pedal RPM
# If measuring pedal RPM, calibration should account for gear ratio
speed_sensor.set_wheel_circumference(2.075)  # 26-inch wheel circumference in meters
speed_sensor.set_calibration_from_wheel_rpm(48.28, 388)  # 30 mph at 388 wheel RPM
pwm = PWM(Pin(LCD.BL)) # Screen Brightness
pwm.freq(1000)
pwm.duty_u16(65535) # Full brightness
back_col = 0

# Incline control constants
INCLINE_STEP = 5.0  # Change incline by 5% per button press
MAX_INCLINE = 100.0  # Maximum incline (100%)
MIN_INCLINE = -100.0  # Maximum decline (-100%)

# =========== Main ============

# Background color - black
LCD.fill(ColorHelper.rgb_color(0,0,0))
# Initial display of all components
#temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
# Display motor and crank counts
motor_display_y = 30 + 61 + (18 * 4) + 18  # Below incline display
motor_sensor.update_display(LCD, ColorHelper.rgb_color, back_col, start_y=motor_display_y)
# Apply initial load based on starting gear
load_controller.apply_load()
LCD.show()

# Define pins for buttons and Joystick
keyA = Pin(15,Pin.IN,Pin.PULL_UP) # Normally 1 but 0 if pressed
keyB = Pin(17,Pin.IN,Pin.PULL_UP)
keyX = Pin(19,Pin.IN,Pin.PULL_UP)
keyY= Pin(21,Pin.IN,Pin.PULL_UP)

up = Pin(2,Pin.IN,Pin.PULL_UP)
down = Pin(18,Pin.IN,Pin.PULL_UP)
left = Pin(16,Pin.IN,Pin.PULL_UP)
right = Pin(20,Pin.IN,Pin.PULL_UP)
ctrl = Pin(3,Pin.IN,Pin.PULL_UP)

LCD.show()

running = True # Loop control

# Display update timing - update 4 times per second (every 250ms)
display_update_interval_ms = 250
last_display_update_time = utime.ticks_ms()

# =========== Main loop ===============
while(running):
    if keyA.value() == 0 and keyY.value() != 0:
        # Toggle speed unit between kmph and mph (only if keyY is not pressed)
        new_unit = speed_sensor.toggle_unit()
        # Clear screen before redrawing
        LCD.fill(back_col)
        # Force immediate display update with new unit
        speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
        LCD.show()
        last_display_update_time = utime.ticks_ms()  # Reset timer
        utime.sleep_ms(200)  # Debounce delay

    if keyB.value() == 0:
        # Toggle simulated RPM on/off
        is_enabled = speed_sensor.toggle_simulated_rpm()
        # Force immediate display update
        LCD.fill(back_col)
        speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
        LCD.show()
        last_display_update_time = utime.ticks_ms()  # Reset timer
        utime.sleep_ms(200)  # Debounce delay

    if keyX.value() == 0:
        # Increase simulated RPM by 10
        speed_sensor.adjust_rpm(10)
        # Force immediate display update
        LCD.fill(back_col)
        speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
        LCD.show()
        last_display_update_time = utime.ticks_ms()  # Reset timer
        utime.sleep_ms(200)  # Debounce delay

    if keyY.value() == 0 and keyA.value() != 0:
        # Decrease simulated RPM by 10
        speed_sensor.adjust_rpm(-10)
        # Force immediate display update
        LCD.fill(back_col)
        speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
        LCD.show()
        last_display_update_time = utime.ticks_ms()  # Reset timer
        utime.sleep_ms(200)  # Debounce delay

    if up.value() == 0:
        # Increase incline (uphill)
        current_incline = load_controller.get_incline()
        new_incline = min(current_incline + INCLINE_STEP, MAX_INCLINE)
        load_controller.set_incline(new_incline)
        # Clear screen and redraw all displays
        LCD.fill(back_col)
        temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
        LCD.show()
        last_display_update_time = utime.ticks_ms()  # Reset timer
        utime.sleep_ms(200)  # Debounce delay

    if down.value() == 0:
        # Decrease incline (downhill)
        current_incline = load_controller.get_incline()
        new_incline = max(current_incline - INCLINE_STEP, MIN_INCLINE)
        load_controller.set_incline(new_incline)
        # Clear screen and redraw all displays
        LCD.fill(back_col)
        temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
        LCD.show()
        last_display_update_time = utime.ticks_ms()  # Reset timer
        utime.sleep_ms(200)  # Debounce delay

    if left.value() == 0:
        # Decrement gear
        if gear_selector.decrement_gear():
            # Update load based on new gear
            load_controller.apply_load()
            # Clear screen and redraw all displays
            LCD.fill(back_col)
            temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
            speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
            gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
            LCD.show()
            last_display_update_time = utime.ticks_ms()  # Reset timer
            utime.sleep_ms(200)  # Debounce delay

    if right.value() == 0:
        # Increment gear
        if gear_selector.increment_gear():
            # Update load based on new gear
            load_controller.apply_load()
            # Clear screen and redraw all displays
            LCD.fill(back_col)
            temp_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
            speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
            gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
            LCD.show()
            last_display_update_time = utime.ticks_ms()  # Reset timer
            utime.sleep_ms(200)  # Debounce delay

    #if (ctrl.value() == 0):
        #print("CTRL")

    # Read current speed (needed for display, but don't use for conditional updates)
    speed_sensor.read_speed()
    
    # Update display 4 times per second (every 250ms)
    current_time = utime.ticks_ms()
    if utime.ticks_diff(current_time, last_display_update_time) >= display_update_interval_ms:
        # Clear screen before redrawing
        LCD.fill(back_col)
        # Redraw all displays
        speed_sensor.update_display(LCD, ColorHelper.rgb_color, back_col)
        gear_selector.update_display(LCD, ColorHelper.rgb_color, back_col)
        # Display motor and crank counts below the speed sensor display
        # Position after incline (speed_y + 61 + 18*4 = speed_y + 133, add 18 more for spacing)
        motor_display_y = 30 + 61 + (18 * 4) + 18  # Below incline display
        motor_sensor.update_display(LCD, ColorHelper.rgb_color, back_col, start_y=motor_display_y)
        LCD.show()
        last_display_update_time = current_time

    if (keyA.value() == 0) and (keyY.value() == 0): # Halt looping?
        running = False

    utime.sleep_us(200) # Debounce delay 

# Finish
LCD.fill(0)
LCD.text("Halted", 95, 115, ColorHelper.rgb_color(255,0,0))
LCD.show()

# Tidy up
utime.sleep(3)
LCD.fill(0)
LCD.show()





