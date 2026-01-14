# Motor Sensor Diagnostic Tool
# This script tests if the motor sensors are working correctly
# Run this to diagnose calibration issues

from machine import Pin
import utime
from Class_MotorSensor import MotorSensor
from Class_LoadController import LoadController
from Class_GearSelector import GearSelector

print("=" * 50)
print("Motor Sensor Diagnostic Tool")
print("=" * 50)
print()

# Initialize components
gear_selector = GearSelector(num_gears=7, min_ratio=1.0, max_ratio=4.5)
motor_sensor = MotorSensor(motor_count_gpio_pin=0, motor_stop_gpio_pin=1)
load_controller = LoadController(l298n_in1_pin=5, l298n_in2_pin=6, gear_selector=gear_selector, motor_sensor=motor_sensor)

print("Initializing sensors...")
print(f"Motor count pin (GPIO 0): {motor_sensor.motor_rpm_pin.value()}")
print(f"Motor stop pin (GPIO 1): {motor_sensor.motor_stop_pin.value()}")
print()

# Test 1: Check initial pin states
print("Test 1: Checking initial pin states")
print("-" * 50)
motor_count_state = motor_sensor.motor_rpm_pin.value()
motor_stop_state = motor_sensor.motor_stop_pin.value()
print(f"GPIO 0 (Motor Count): {motor_count_state} (0=LOW, 1=HIGH)")
print(f"GPIO 1 (Motor Stop): {motor_stop_state} (0=LOW, 1=HIGH)")
print()

# Test 2: Monitor pin states for 5 seconds (check if they're changing)
print("Test 2: Monitoring pin states for 5 seconds")
print("-" * 50)
print("Watch for changes in pin states...")
print("If pins never change, sensors may not be connected or working")
print()

initial_count = motor_sensor.motor_pulse_count
initial_stop_count = motor_sensor.motor_crank_pulse_count
initial_position = motor_sensor.motor_crank_position

pin_changes_0 = 0
pin_changes_1 = 0
last_state_0 = motor_count_state
last_state_1 = motor_stop_state

start_time = utime.ticks_ms()
monitor_duration = 5000  # 5 seconds

while utime.ticks_diff(utime.ticks_ms(), start_time) < monitor_duration:
    current_state_0 = motor_sensor.motor_rpm_pin.value()
    current_state_1 = motor_sensor.motor_stop_pin.value()

    if current_state_0 != last_state_0:
        pin_changes_0 += 1
        last_state_0 = current_state_0
        print(f"GPIO 0 changed to: {current_state_0} (at {utime.ticks_diff(utime.ticks_ms(), start_time)}ms)")

    if current_state_1 != last_state_1:
        pin_changes_1 += 1
        last_state_1 = current_state_1
        print(f"GPIO 1 changed to: {current_state_1} (at {utime.ticks_diff(utime.ticks_ms(), start_time)}ms)")

    utime.sleep_ms(10)

print()
print(f"GPIO 0 changes detected: {pin_changes_0}")
print(f"GPIO 1 changes detected: {pin_changes_1}")
print(f"Motor pulse count: {motor_sensor.motor_pulse_count} (was {initial_count})")
print(f"Motor stop count: {motor_sensor.motor_crank_pulse_count} (was {initial_stop_count})")
print(f"Motor position: {motor_sensor.motor_crank_position} (was {initial_position})")
print()

# Test 3: Try to move motor forward and monitor sensors
print("Test 3: Testing motor movement (forward for 2 seconds)")
print("-" * 50)
print("Starting motor forward...")

initial_count = motor_sensor.motor_pulse_count
initial_position = motor_sensor.motor_crank_position

load_controller.set_motor_direction_forward()
utime.sleep_ms(2000)  # Run for 2 seconds
load_controller.stop_motor()

final_count = motor_sensor.motor_pulse_count
final_position = motor_sensor.motor_crank_position

print(f"Motor pulse count: {initial_count} -> {final_count} (change: {final_count - initial_count})")
print(f"Motor position: {initial_position} -> {final_position} (change: {final_position - initial_position})")

if final_count == initial_count:
    print("WARNING: No pulses detected! Motor sensor (GPIO 0) may not be working.")
    print("Check:")
    print("  - Is the hall sensor connected to GPIO 0?")
    print("  - Is the sensor getting power?")
    print("  - Is the sensor aligned with the motor magnet?")
else:
    print("OK: Motor sensor (GPIO 0) is detecting pulses")
print()

# Test 4: Try to move motor reverse and monitor sensors
print("Test 4: Testing motor movement (reverse for 2 seconds)")
print("-" * 50)
print("Starting motor reverse...")

initial_count = motor_sensor.motor_pulse_count
initial_position = motor_sensor.motor_crank_position

load_controller.set_motor_direction_reverse()
utime.sleep_ms(2000)  # Run for 2 seconds
load_controller.stop_motor()

final_count = motor_sensor.motor_pulse_count
final_position = motor_sensor.motor_crank_position

print(f"Motor pulse count: {initial_count} -> {final_count} (change: {final_count - initial_count})")
print(f"Motor position: {initial_position} -> {final_position} (change: {final_position - initial_position})")

if final_count == initial_count:
    print("WARNING: No pulses detected during reverse! Motor sensor (GPIO 0) may not be working.")
else:
    print("OK: Motor sensor (GPIO 0) is detecting pulses in reverse")
print()

# Test 5: Check motor stop trigger
print("Test 5: Testing motor stop trigger (GPIO 1)")
print("-" * 50)
print("Current stop pin state:", motor_sensor.motor_stop_pin.value())
print("Is at bottom:", motor_sensor.is_motor_crank_at_bottom())
print()
print("Note: The motor may need up to 1000 motor rotations to reach")
print("      the stop position, depending on initial position.")
print("      This can take 5-10 minutes if the motor is slow.")
print("      Progress will be shown every 5 seconds.")
print()

# Try moving forward slowly to see if we can trigger the stop sensor
print("Moving forward slowly to find stop trigger...")
print("Maximum timeout: 10 minutes (600 seconds)")
print()

load_controller.set_motor_direction_forward()

stop_triggered = False
start_time = utime.ticks_ms()
timeout = 600000  # 10 minute timeout (600 seconds) to allow for up to 1000 rotations
last_status_time = start_time
status_interval = 5000  # Print status every 5 seconds
last_pulse_count = 0
last_pulse_time = start_time

initial_pulse_count = motor_sensor.motor_pulse_count
max_rotations_needed = 1000  # Worst case: need to do a full rotation

while utime.ticks_diff(utime.ticks_ms(), start_time) < timeout:
    elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
    current_pulses = motor_sensor.motor_pulse_count
    pulse_diff = current_pulses - initial_pulse_count

    # Print progress every 5 seconds
    if utime.ticks_diff(utime.ticks_ms(), last_status_time) >= status_interval:
        elapsed_sec = elapsed // 1000
        elapsed_min = elapsed_sec // 60
        elapsed_sec_remainder = elapsed_sec % 60

        # Calculate pulse rate (rotations per second)
        if pulse_diff > last_pulse_count:
            time_since_last = utime.ticks_diff(utime.ticks_ms(), last_pulse_time)
            if time_since_last > 0:
                pulse_rate = (pulse_diff - last_pulse_count) * 1000 / time_since_last
            else:
                pulse_rate = 0
        else:
            pulse_rate = 0

        # Estimate remaining rotations and time
        remaining_rotations = max_rotations_needed - pulse_diff
        if pulse_rate > 0 and remaining_rotations > 0:
            est_seconds_remaining = int(remaining_rotations / pulse_rate)
            est_min_remaining = est_seconds_remaining // 60
            est_sec_remaining = est_seconds_remaining % 60
            time_estimate = f"~{est_min_remaining}m {est_sec_remaining}s remaining"
        else:
            time_estimate = "calculating..."

        print(f"  Progress: {elapsed_min}m {elapsed_sec_remainder}s elapsed, "
              f"{pulse_diff}/1000 rotations, {time_estimate}")

        last_status_time = utime.ticks_ms()
        last_pulse_count = pulse_diff
        last_pulse_time = utime.ticks_ms()

    if motor_sensor.motor_stop_pin.value() == 1:
        elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
        elapsed_sec = elapsed // 1000
        elapsed_min = elapsed_sec // 60
        elapsed_sec_remainder = elapsed_sec % 60
        pulse_diff = motor_sensor.motor_pulse_count - initial_pulse_count
        print(f"Stop trigger detected! (at {elapsed_min}m {elapsed_sec_remainder}s, {pulse_diff} rotations)")
        stop_triggered = True
        break
    utime.sleep_ms(10)

load_controller.stop_motor()

if not stop_triggered:
    elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
    elapsed_sec = elapsed // 1000
    elapsed_min = elapsed_sec // 60
    elapsed_sec_remainder = elapsed_sec % 60
    pulse_diff = motor_sensor.motor_pulse_count - initial_pulse_count
    print(f"WARNING: Stop trigger not detected after {elapsed_min}m {elapsed_sec_remainder}s!")
    print(f"Motor moved {pulse_diff} rotations (out of up to 1000 needed) but stop trigger was not found.")
    if pulse_diff >= 1000:
        print("Motor completed a full rotation but stop trigger was never detected.")
        print("This suggests the stop sensor may not be working correctly.")
    else:
        print(f"Motor may need {1000 - pulse_diff} more rotations to reach stop position.")
        print("Consider increasing timeout or checking if motor is moving too slowly.")
    print("Check:")
    print("  - Is the stop sensor connected to GPIO 1?")
    print("  - Is the sensor getting power?")
    print("  - Is the sensor aligned with the motor crank?")
    print("  - Is the motor actually rotating? (check pulse count)")
else:
    print("OK: Motor stop trigger (GPIO 1) is working")
print()

# Summary
print("=" * 50)
print("Diagnostic Summary")
print("=" * 50)
print(f"GPIO 0 (Motor Count) changes: {pin_changes_0}")
print(f"GPIO 1 (Motor Stop) changes: {pin_changes_1}")
print(f"Motor pulses detected: {motor_sensor.motor_pulse_count > 0}")
print(f"Stop trigger working: {stop_triggered}")
print()

if pin_changes_0 == 0 and motor_sensor.motor_pulse_count == 0:
    print("ISSUE: Motor count sensor (GPIO 0) is not detecting any pulses")
    print("This will prevent calibration from working!")
elif motor_sensor.motor_pulse_count > 0:
    print("OK: Motor count sensor (GPIO 0) appears to be working")

if not stop_triggered:
    print("ISSUE: Motor stop trigger (GPIO 1) is not working")
    print("This will prevent calibration from completing!")
else:
    print("OK: Motor stop trigger (GPIO 1) appears to be working")

print()
print("Diagnostic complete!")
