# WaceShare Library code
# Alistair Mcgranaghan 24/09/2022
from machine import Pin, PWM
import utime
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
from Class_TimerController import TimerController

# BLE support (optional - requires Pico W)
try:
    from Class_BLEController import BLEController
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False
    print("Note: BLE not available (requires Pico W or ubluetooth module)")

# =========== Configuration Constants ===========
# Motor configuration
MOTOR_COUNT_GPIO_PIN = 0
MOTOR_STOP_GPIO_PIN = 1
L298N_IN1_PIN = 5
L298N_IN2_PIN = 6

# Sensor GPIO pins
CRANK_SENSOR_GPIO = 7
WHEEL_SPEED_SENSOR_GPIO = 4

# Gear configuration
NUM_GEARS = 7
MIN_GEAR_RATIO = 1.0
MAX_GEAR_RATIO = 4.5

# Wheel configuration
WHEEL_CIRCUMFERENCE_M = 2.075  # 26-inch wheel circumference in meters
CALIBRATION_SPEED_KMH = 48.28  # Known speed for calibration
CALIBRATION_WHEEL_RPM = 388  # Wheel RPM at known speed

# Button configuration
INCLINE_STEP = 5.0
MAX_INCLINE = 100.0
MIN_INCLINE = -100.0

# Display configuration
DISPLAY_UPDATE_INTERVAL_MS = 250  # Update 4 times per second
MAIN_LOOP_SLEEP_US = 200  # Small delay to prevent tight loop
CALIBRATION_DELAY_SEC = 3  # Wait before starting calibration

# BLE configuration
BLE_ENABLED = True  # Set to False to disable BLE (requires Pico W)
BLE_UPDATE_INTERVAL_MS = 1000  # Update BLE data every second

# Error handling configuration
ERROR_RETRY_DELAY_MS = 1000  # Delay after error before retry
MAX_CONSECUTIVE_ERRORS = 10  # Maximum consecutive errors before giving up

# =========== Initialization ===========
try:
    LCD = LCD_Driver_Class()
    gear_selector = GearSelector(num_gears=NUM_GEARS, min_ratio=MIN_GEAR_RATIO, max_ratio=MAX_GEAR_RATIO)
    motor_sensor = MotorSensor(motor_count_gpio_pin=MOTOR_COUNT_GPIO_PIN, motor_stop_gpio_pin=MOTOR_STOP_GPIO_PIN)
    load_controller = LoadController(
        l298n_in1_pin=L298N_IN1_PIN,
        l298n_in2_pin=L298N_IN2_PIN,
        gear_selector=gear_selector,
        motor_sensor=motor_sensor,
        lcd=LCD,
        rgb_color_func=ColorHelper.rgb_color
    )

    # Wait before starting calibration
    utime.sleep(CALIBRATION_DELAY_SEC)

    # Perform startup calibration: move to bottom position, then to top position (180 degrees)
    load_controller.startup_calibration()

    # Crank sensor (measures pedal/crank speed - returns RPM only)
    crank_sensor = CrankSensor(gpio_pin=CRANK_SENSOR_GPIO)

    # Wheel speed sensor (measures flywheel/wheel speed directly - returns RPM only)
    wheel_speed_sensor = WheelSpeedSensor(gpio_pin=WHEEL_SPEED_SENSOR_GPIO)

    # Speed controller (manages all speed calculations - always displays mph)
    speed_controller = SpeedController(
        crank_sensor=crank_sensor,
        wheel_speed_sensor=wheel_speed_sensor,
        gear_selector=gear_selector,
        load_controller=load_controller,
        unit='mph'  # Always use mph
    )
    speed_controller.set_wheel_circumference(WHEEL_CIRCUMFERENCE_M)
    speed_controller.set_calibration_from_wheel_rpm(CALIBRATION_SPEED_KMH, CALIBRATION_WHEEL_RPM)

    # Initialize timer controller (manages timer functionality - MVC pattern)
    timer_controller = TimerController()

    # Initialize BLE controller (optional - requires Pico W)
    ble_controller = None
    if BLE_AVAILABLE and BLE_ENABLED:
        try:
            ble_controller = BLEController(
                name="Pico Bike Trainer",
                speed_controller=speed_controller,
                load_controller=load_controller
            )
            ble_controller.set_wheel_circumference(int(WHEEL_CIRCUMFERENCE_M * 1000))  # Convert to mm
            print("BLE controller initialized")
        except Exception as e:
            print(f"Warning: Failed to initialize BLE: {e}")
            print("Continuing without BLE support...")
            ble_controller = None

    # Initialize view (handles all display logic - MVC pattern)
    back_col = 0
    view = View(
        LCD, ColorHelper.rgb_color, back_col,
        speed_controller=speed_controller,
        gear_selector=gear_selector,
        load_controller=load_controller,
        timer_controller=timer_controller,
        ble_controller=ble_controller,
        screen_width=LCD.width,
        screen_height=LCD.height
    )

    # Initialize button controller (handles all button inputs - MVC pattern)
    button_controller = ButtonController(
        speed_controller=speed_controller,
        load_controller=load_controller,
        gear_selector=gear_selector,
        timer_controller=timer_controller,
        ble_controller=ble_controller,
        view=view,
        incline_step=INCLINE_STEP,
        max_incline=MAX_INCLINE,
        min_incline=MIN_INCLINE
    )

    # Screen brightness
    pwm = PWM(Pin(LCD.BL))
    pwm.freq(1000)
    pwm.duty_u16(65535)  # Full brightness

    # Initialize display
    LCD.fill(ColorHelper.rgb_color(0, 0, 0))
    load_controller.apply_load()
    view.render_all()
    LCD.show()

except Exception as e:
    print(f"FATAL ERROR during initialization: {e}")
    # Try to show error on display if possible
    try:
        LCD.fill(0)
        LCD.write_text("INIT ERROR", 50, 100, 2, ColorHelper.rgb_color(255, 0, 0))
        LCD.show()
    except:
        pass
    # Halt execution
    while True:
        utime.sleep_ms(1000)

# =========== Main Loop ===========
last_display_update_time = utime.ticks_ms()
last_ble_update_time = utime.ticks_ms()
consecutive_errors = 0

while True:
    try:
        current_time = utime.ticks_ms()

        # Check all buttons and handle actions
        button_controller.check_buttons()

        # Continuously update load to adjust motor position towards target
        load_controller.apply_load()

        # Update BLE data if enabled
        if ble_controller is not None:
            # Update pairing mode (check for timeout)
            ble_controller.update_pairing_mode(current_time)

            if utime.ticks_diff(current_time, last_ble_update_time) >= BLE_UPDATE_INTERVAL_MS:
                ble_controller.update_combined_data()
                ble_controller.update_incline_value()
                last_ble_update_time = current_time

        # Update display at configured interval
        if utime.ticks_diff(current_time, last_display_update_time) >= DISPLAY_UPDATE_INTERVAL_MS:
            view.render_all()
            last_display_update_time = current_time

        # Reset error counter on successful iteration
        consecutive_errors = 0

        utime.sleep_us(MAIN_LOOP_SLEEP_US)

    except Exception as e:
        consecutive_errors += 1
        print(f"Error in main loop (count: {consecutive_errors}): {e}")

        # If too many consecutive errors, try to show error and halt
        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            print("Too many consecutive errors - halting")
            try:
                LCD.fill(0)
                LCD.write_text("SYSTEM ERROR", 30, 100, 2, ColorHelper.rgb_color(255, 0, 0))
                LCD.show()
                load_controller.stop_motor()  # Ensure motor is stopped
            except:
                pass
            # Halt execution
            while True:
                utime.sleep_ms(1000)

        # Wait before retrying
        utime.sleep_ms(ERROR_RETRY_DELAY_MS)





