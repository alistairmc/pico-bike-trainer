# Crank and Wheel Speed Sensor Diagnostic Tool
# This script tests if the crank and wheel speed sensors are working correctly
# Run this to diagnose speed sensor issues

from machine import Pin
import utime
from Class_CrankSensor import CrankSensor
from Class_WheelSpeedSensor import WheelSpeedSensor
from Class_SpeedController import SpeedController
from Class_GearSelector import GearSelector

print("=" * 60)
print("Crank and Wheel Speed Sensor Diagnostic Tool")
print("=" * 60)
print()

# Initialize components
gear_selector = GearSelector(num_gears=7, min_ratio=1.0, max_ratio=4.5)
crank_sensor = CrankSensor(gpio_pin=7)
wheel_speed_sensor = WheelSpeedSensor(gpio_pin=4)
speed_controller = SpeedController(
    crank_sensor=crank_sensor,
    wheel_speed_sensor=wheel_speed_sensor,
    gear_selector=gear_selector
)
speed_controller.set_wheel_circumference(2.075)  # 26-inch wheel

print("Initializing sensors...")
print(f"Crank sensor pin (GPIO 7): {crank_sensor.hall_sensor.value()}")
print(f"Wheel sensor pin (GPIO 4): {wheel_speed_sensor.hall_sensor.value()}")
print()

# Test 1: Check initial pin states
print("Test 1: Checking initial pin states")
print("-" * 60)
crank_state = crank_sensor.hall_sensor.value()
wheel_state = wheel_speed_sensor.hall_sensor.value()
print(f"GPIO 7 (Crank Sensor): {crank_state} (0=LOW, 1=HIGH)")
print(f"GPIO 4 (Wheel Sensor): {wheel_state} (0=LOW, 1=HIGH)")
print()

# Test 2: Monitor pin states for 10 seconds (check if they're changing)
print("Test 2: Monitoring pin states for 10 seconds")
print("-" * 60)
print("Watch for changes in pin states...")
print("If pins never change, sensors may not be connected or working")
print("Start pedaling/spinning the wheel now!")
print()

initial_crank_count = crank_sensor.pulse_count
initial_wheel_count = wheel_speed_sensor.pulse_count

pin_changes_crank = 0
pin_changes_wheel = 0
last_state_crank = crank_state
last_state_wheel = wheel_state

start_time = utime.ticks_ms()
monitor_duration = 10000  # 10 seconds

while utime.ticks_diff(utime.ticks_ms(), start_time) < monitor_duration:
    current_state_crank = crank_sensor.hall_sensor.value()
    current_state_wheel = wheel_speed_sensor.hall_sensor.value()
    
    if current_state_crank != last_state_crank:
        pin_changes_crank += 1
        last_state_crank = current_state_crank
        elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
        print(f"  GPIO 7 (Crank) changed to: {current_state_crank} (at {elapsed}ms)")
    
    if current_state_wheel != last_state_wheel:
        pin_changes_wheel += 1
        last_state_wheel = current_state_wheel
        elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
        print(f"  GPIO 4 (Wheel) changed to: {current_state_wheel} (at {elapsed}ms)")
    
    utime.sleep_ms(10)

print()
print(f"GPIO 7 (Crank) changes detected: {pin_changes_crank}")
print(f"GPIO 4 (Wheel) changes detected: {pin_changes_wheel}")
print(f"Crank pulse count: {crank_sensor.pulse_count} (was {initial_crank_count})")
print(f"Wheel pulse count: {wheel_speed_sensor.pulse_count} (was {initial_wheel_count})")
print()

# Test 3: Monitor RPM readings for 30 seconds
print("Test 3: Monitoring RPM readings for 30 seconds")
print("-" * 60)
print("Keep pedaling/spinning the wheel...")
print("RPM readings will be shown every 2 seconds")
print()

start_time = utime.ticks_ms()
monitor_duration = 30000  # 30 seconds
update_interval = 2000  # Update every 2 seconds
last_update_time = start_time

max_crank_rpm = 0
max_wheel_rpm = 0
min_crank_rpm = 999999
min_wheel_rpm = 999999
rpm_readings_crank = []
rpm_readings_wheel = []

while utime.ticks_diff(utime.ticks_ms(), start_time) < monitor_duration:
    elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
    
    if utime.ticks_diff(utime.ticks_ms(), last_update_time) >= update_interval:
        crank_rpm = crank_sensor.get_rpm()
        wheel_rpm = wheel_speed_sensor.get_rpm()
        
        if crank_rpm > 0:
            rpm_readings_crank.append(crank_rpm)
            if crank_rpm > max_crank_rpm:
                max_crank_rpm = crank_rpm
            if crank_rpm < min_crank_rpm:
                min_crank_rpm = crank_rpm
        
        if wheel_rpm > 0:
            rpm_readings_wheel.append(wheel_rpm)
            if wheel_rpm > max_wheel_rpm:
                max_wheel_rpm = wheel_rpm
            if wheel_rpm < min_wheel_rpm:
                min_wheel_rpm = wheel_rpm
        
        elapsed_sec = elapsed // 1000
        print(f"  [{elapsed_sec:3d}s] Crank RPM: {crank_rpm:4d}  |  Wheel RPM: {wheel_rpm:4d}")
        
        last_update_time = utime.ticks_ms()
    
    utime.sleep_ms(100)

print()
if len(rpm_readings_crank) > 0:
    avg_crank_rpm = sum(rpm_readings_crank) // len(rpm_readings_crank)
    print(f"Crank RPM - Min: {min_crank_rpm}, Max: {max_crank_rpm}, Avg: {avg_crank_rpm}")
else:
    print("Crank RPM - No readings detected!")

if len(rpm_readings_wheel) > 0:
    avg_wheel_rpm = sum(rpm_readings_wheel) // len(rpm_readings_wheel)
    print(f"Wheel RPM - Min: {min_wheel_rpm}, Max: {max_wheel_rpm}, Avg: {avg_wheel_rpm}")
else:
    print("Wheel RPM - No readings detected!")
print()

# Test 4: Test speed calculations with different gears
print("Test 4: Testing speed calculations with different gears")
print("-" * 60)
print("This test shows how speed changes with different gear ratios")
print("Keep pedaling at a steady rate...")
print()

# Test each gear
for gear_num in range(1, gear_selector.num_gears + 1):
    gear_selector.current_gear = gear_num
    gear_ratio = gear_selector.get_current_ratio()
    
    # Wait a moment for RPM to stabilize
    utime.sleep_ms(2000)
    
    # Get current readings
    crank_rpm = crank_sensor.get_rpm()
    wheel_rpm = wheel_speed_sensor.get_rpm()
    calculated_speed = speed_controller.get_calculated_speed()
    unit_label = speed_controller.unit
    
    print(f"Gear {gear_num} (Ratio: {gear_ratio:.2f}):")
    print(f"  Crank RPM: {crank_rpm}")
    print(f"  Wheel RPM: {wheel_rpm}")
    print(f"  Calculated Speed: {calculated_speed:.1f} {unit_label}")
    print(f"  (Wheel {wheel_rpm} RPM × {gear_ratio:.2f} = {wheel_rpm * gear_ratio:.1f} virtual RPM)")
    print()

# Test 5: Real-time monitoring with calculated speed
print("Test 5: Real-time monitoring (20 seconds)")
print("-" * 60)
print("Keep pedaling...")
print("Shows: Crank RPM, Wheel RPM, Calculated Speed (current gear)")
print()

start_time = utime.ticks_ms()
monitor_duration = 20000  # 20 seconds
update_interval = 1000  # Update every 1 second
last_update_time = start_time

print(f"{'Time':<6} {'Gear':<5} {'CRPM':<6} {'WRPM':<6} {'Speed (kmph)':<12} {'Speed (mph)':<12}")
print("-" * 60)

while utime.ticks_diff(utime.ticks_ms(), start_time) < monitor_duration:
    elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
    
    if utime.ticks_diff(utime.ticks_ms(), last_update_time) >= update_interval:
        crank_rpm = crank_sensor.get_rpm()
        wheel_rpm = wheel_speed_sensor.get_rpm()
        current_gear = gear_selector.current_gear
        
        # Get speed in current unit
        calculated_speed = speed_controller.get_calculated_speed()
        
        # Also get speed in both units for display
        original_unit = speed_controller.unit
        speed_controller.unit = 'kmph'
        speed_kmph = speed_controller.get_calculated_speed()
        speed_controller.unit = 'mph'
        speed_mph = speed_controller.get_calculated_speed()
        speed_controller.unit = original_unit  # Restore original unit
        
        elapsed_sec = elapsed // 1000
        print(f"{elapsed_sec:4d}s  {current_gear:3d}   {crank_rpm:4d}   {wheel_rpm:4d}   {speed_kmph:10.1f}      {speed_mph:10.1f}")
        
        last_update_time = utime.ticks_ms()
    
    utime.sleep_ms(100)

print()

# Summary
print("=" * 60)
print("Diagnostic Summary")
print("=" * 60)
print(f"GPIO 7 (Crank) pin changes: {pin_changes_crank}")
print(f"GPIO 4 (Wheel) pin changes: {pin_changes_wheel}")
print(f"Crank pulses detected: {crank_sensor.pulse_count}")
print(f"Wheel pulses detected: {wheel_speed_sensor.pulse_count}")
print()

if pin_changes_crank == 0 and crank_sensor.pulse_count == 0:
    print("ISSUE: Crank sensor (GPIO 7) is not detecting any pulses")
    print("Check:")
    print("  - Is the hall sensor connected to GPIO 7?")
    print("  - Is the sensor getting power?")
    print("  - Is the sensor aligned with the crank magnet?")
    print("  - Are you pedaling the bike?")
elif crank_sensor.pulse_count > 0:
    print("OK: Crank sensor (GPIO 7) appears to be working")
    if len(rpm_readings_crank) > 0:
        print(f"     Detected RPM range: {min_crank_rpm} - {max_crank_rpm} RPM")

if pin_changes_wheel == 0 and wheel_speed_sensor.pulse_count == 0:
    print("ISSUE: Wheel speed sensor (GPIO 4) is not detecting any pulses")
    print("Check:")
    print("  - Is the hall sensor connected to GPIO 4?")
    print("  - Is the sensor getting power?")
    print("  - Is the sensor aligned with the wheel magnet?")
    print("  - Is the wheel/flywheel spinning?")
elif wheel_speed_sensor.pulse_count > 0:
    print("OK: Wheel speed sensor (GPIO 4) appears to be working")
    if len(rpm_readings_wheel) > 0:
        print(f"     Detected RPM range: {min_wheel_rpm} - {max_wheel_rpm} RPM")

print()
print("Diagnostic complete!")
