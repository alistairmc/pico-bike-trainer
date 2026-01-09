# Gear Ratio Calculator
# This script calculates the fixed gear ratio between crank and wheel sensors
# Run this while pedaling at various speeds to determine the physical gear ratio
# The ratio is calculated as: Wheel RPM / Crank RPM

from machine import Pin
import utime
from Class_CrankSensor import CrankSensor
from Class_WheelSpeedSensor import WheelSpeedSensor
from Class_MotorSensor import MotorSensor
from Class_LoadController import LoadController
from Class_GearSelector import GearSelector

print("=" * 60)
print("Gear Ratio Calculator")
print("=" * 60)
print()
print("This script calculates the fixed gear ratio between:")
print("  - Crank sensor (GPIO 7)")
print("  - Wheel sensor (GPIO 4)")
print()
print("Ratio = Wheel RPM / Crank RPM")
print()
print("Instructions:")
print("  1. Start pedaling at a steady, comfortable pace")
print("  2. Keep pedaling for the duration of the test")
print("  3. Try different pedaling speeds if possible")
print("  4. The script will collect data and calculate statistics")
print()
print("Note: The wheel (flywheel) has inertia and may continue spinning")
print("      after you stop pedaling. The script will ignore these cases")
print("      and only calculate ratios when you are actively pedaling.")
print()
print("Note: Load will be set to minimum (0%) for accurate ratio calculation.")
print()

# Initialize sensors
crank_sensor = CrankSensor(gpio_pin=7)
wheel_speed_sensor = WheelSpeedSensor(gpio_pin=4)

print("Sensors initialized")
print(f"  Crank sensor (GPIO 7): {crank_sensor.hall_sensor.value()}")
print(f"  Wheel sensor (GPIO 4): {wheel_speed_sensor.hall_sensor.value()}")
print()

# Initialize load controller to set load to minimum
print("Initializing load controller...")
gear_selector = GearSelector(num_gears=7, min_ratio=1.0, max_ratio=4.5)
motor_sensor = MotorSensor(motor_count_gpio_pin=0, motor_stop_gpio_pin=1)
load_controller = LoadController(
    l298n_in1_pin=5, 
    l298n_in2_pin=6, 
    gear_selector=gear_selector, 
    motor_sensor=motor_sensor
)

# Set load to absolute minimum (0%) by moving motor until stop pulse is triggered
print("Setting load to minimum (0%)...")
print("  Moving motor until stop pulse is detected...")
print("  This may take up to 2 minutes depending on motor position...")

# Move motor until stop trigger is detected (position 0 = 0% load)
if load_controller.motor_sensor is not None:
    # Check if already at stop position
    if load_controller.motor_sensor.motor_stop_pin.value() == 1:
        print("  Motor already at stop position (0% load)")
    else:
        # Temporarily disable interrupt to avoid false positives
        load_controller.motor_sensor.disable_stop_interrupt()
        
        # Move motor forward until stop trigger is detected
        load_controller.set_motor_direction_forward()
        
        # Wait for stop trigger with timeout
        stop_detected = False
        debounce_count = 0
        required_high_readings = 10
        timeout_ms = 120000  # 2 minute timeout
        start_time = utime.ticks_ms()
        last_status_time = start_time
        
        print("  Searching for stop position...")
        
        while debounce_count < required_high_readings:
            elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
            
            # Show progress every 5 seconds
            if utime.ticks_diff(utime.ticks_ms(), last_status_time) >= 5000:
                elapsed_sec = elapsed // 1000
                print(f"  Still searching... {elapsed_sec}s elapsed")
                last_status_time = utime.ticks_ms()
            
            if elapsed > timeout_ms:
                print(f"  Timeout: Stop trigger not detected after {elapsed // 1000}s")
                load_controller.stop_motor()
                load_controller.motor_sensor.enable_stop_interrupt()
                break
            
            pin_value = load_controller.motor_sensor.motor_stop_pin.value()
            if pin_value == 1:  # HIGH - stop pulse detected
                debounce_count += 1
            else:
                debounce_count = 0
            
            utime.sleep_ms(10)
        
        if debounce_count >= required_high_readings:
            # Stop trigger detected
            load_controller.stop_motor()
            utime.sleep_ms(300)  # Pause to ensure motor stops
            
            # Sync position to sensor (reset to 0)
            load_controller.motor_sensor.sync_position_to_sensor()
            stop_detected = True
            elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
            print(f"  Stop trigger detected! (took {elapsed // 1000}s)")
        
        # Re-enable interrupt handler
        load_controller.motor_sensor.enable_stop_interrupt()
        
        if stop_detected:
            print("  Load set to minimum (0% - stop position)")
        else:
            print("  Warning: Could not reach stop position")
            print("  Setting gear to 1 and incline to -100% as fallback...")
            gear_selector.current_gear = 1
            load_controller.set_incline(-100.0)
            load_controller.apply_load()
else:
    # No motor sensor, use gear and incline method
    print("  No motor sensor - using gear/incline method...")
    gear_selector.current_gear = 1
    load_controller.set_incline(-100.0)
    load_controller.apply_load()

print("Load set to minimum")
print()
print("Starting data collection in 3 seconds...")
print("Start pedaling now!")
print()

utime.sleep(3)

# Data collection parameters
collection_duration = 60000  # 60 seconds
update_interval = 1000  # Update every 1 second
sample_interval = 200  # Sample every 200ms for more data points
min_crank_rpm_threshold = 15  # Minimum crank RPM to consider valid (filters out coasting)

start_time = utime.ticks_ms()
last_display_time = start_time
last_sample_time = start_time

ratios = []
crank_rpms = []
wheel_rpms = []
valid_samples = 0
invalid_samples = 0
coasting_samples = 0  # Wheel spinning but crank not (flywheel inertia)

print(f"{'Time':<6} {'CRPM':<6} {'WRPM':<6} {'Ratio':<8} {'Status':<15}")
print("-" * 60)

while utime.ticks_diff(utime.ticks_ms(), start_time) < collection_duration:
    elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
    
    # Sample data every sample_interval
    if utime.ticks_diff(utime.ticks_ms(), last_sample_time) >= sample_interval:
        crank_rpm = crank_sensor.get_rpm()
        wheel_rpm = wheel_speed_sensor.get_rpm()
        
        # Only calculate ratio if both sensors have valid readings AND crank is actively being pedaled
        # This filters out cases where the wheel is coasting due to flywheel inertia
        if crank_rpm >= min_crank_rpm_threshold and wheel_rpm > 0:
            # Actively pedaling - valid sample
            ratio = wheel_rpm / crank_rpm
            ratios.append(ratio)
            crank_rpms.append(crank_rpm)
            wheel_rpms.append(wheel_rpm)
            valid_samples += 1
        elif wheel_rpm > 0 and crank_rpm < min_crank_rpm_threshold:
            # Wheel spinning but crank not - flywheel coasting, ignore this
            coasting_samples += 1
        else:
            # No valid readings from either sensor
            invalid_samples += 1
        
        last_sample_time = utime.ticks_ms()
    
    # Display status every update_interval
    if utime.ticks_diff(utime.ticks_ms(), last_display_time) >= update_interval:
        elapsed_sec = elapsed // 1000
        current_crank_rpm = crank_sensor.get_rpm()
        current_wheel_rpm = wheel_speed_sensor.get_rpm()
        
        if current_crank_rpm >= min_crank_rpm_threshold and current_wheel_rpm > 0:
            current_ratio = current_wheel_rpm / current_crank_rpm
            status = "Pedaling"
        elif current_wheel_rpm > 0 and current_crank_rpm < min_crank_rpm_threshold:
            current_ratio = 0.0
            status = "Coasting"
        else:
            current_ratio = 0.0
            if current_crank_rpm == 0 and current_wheel_rpm == 0:
                status = "No signal"
            elif current_crank_rpm == 0:
                status = "No crank"
            else:
                status = "No wheel"
        
        print(f"{elapsed_sec:4d}s  {current_crank_rpm:4d}   {current_wheel_rpm:4d}   {current_ratio:7.3f}  {status}")
        
        last_display_time = utime.ticks_ms()
    
    utime.sleep_ms(50)

print()
print("=" * 60)
print("Data Collection Complete")
print("=" * 60)
print()

if len(ratios) == 0:
    print("ERROR: No valid data collected!")
    print("Check:")
    print("  - Are both sensors connected?")
    print("  - Are you pedaling the bike?")
    print("  - Are the sensors aligned with magnets?")
    print()
    print(f"Valid samples (pedaling): {valid_samples}")
    print(f"Coasting samples (ignored): {coasting_samples}")
    print(f"Invalid samples: {invalid_samples}")
    if coasting_samples > 0:
        print()
        print(f"Note: {coasting_samples} samples were ignored because the wheel was")
        print(f"      coasting (crank RPM < {min_crank_rpm_threshold}).")
        print(f"      Make sure you are actively pedaling during the test.")
else:
    # Calculate statistics
    min_ratio = min(ratios)
    max_ratio = max(ratios)
    avg_ratio = sum(ratios) / len(ratios)
    
    # Calculate median
    sorted_ratios = sorted(ratios)
    if len(sorted_ratios) % 2 == 0:
        median_ratio = (sorted_ratios[len(sorted_ratios)//2 - 1] + sorted_ratios[len(sorted_ratios)//2]) / 2
    else:
        median_ratio = sorted_ratios[len(sorted_ratios)//2]
    
    # Calculate standard deviation
    variance = sum((r - avg_ratio) ** 2 for r in ratios) / len(ratios)
    std_dev = variance ** 0.5
    
    # Find most common ratio (mode approximation - bin to 0.01)
    ratio_bins = {}
    for ratio in ratios:
        bin_key = round(ratio * 100) / 100  # Round to 0.01
        ratio_bins[bin_key] = ratio_bins.get(bin_key, 0) + 1
    
    mode_ratio = max(ratio_bins, key=ratio_bins.get)
    mode_count = ratio_bins[mode_ratio]
    
    # RPM statistics
    min_crank_rpm = min(crank_rpms)
    max_crank_rpm = max(crank_rpms)
    avg_crank_rpm = sum(crank_rpms) / len(crank_rpms)
    
    min_wheel_rpm = min(wheel_rpms)
    max_wheel_rpm = max(wheel_rpms)
    avg_wheel_rpm = sum(wheel_rpms) / len(wheel_rpms)
    
    print("Statistics:")
    print("-" * 60)
    print(f"Total samples collected: {len(ratios)}")
    print(f"Valid samples (pedaling): {valid_samples}")
    print(f"Coasting samples (ignored): {coasting_samples}")
    print(f"Invalid samples: {invalid_samples}")
    print()
    print(f"Note: Samples where wheel was spinning but crank RPM < {min_crank_rpm_threshold}")
    print(f"      were ignored to filter out flywheel coasting effects.")
    print()
    
    print("Gear Ratio Statistics:")
    print(f"  Minimum ratio: {min_ratio:.4f}")
    print(f"  Maximum ratio: {max_ratio:.4f}")
    print(f"  Average ratio: {avg_ratio:.4f}")
    print(f"  Median ratio:  {median_ratio:.4f}")
    print(f"  Mode ratio:    {mode_ratio:.4f} (appears {mode_count} times)")
    print(f"  Std deviation: {std_dev:.4f}")
    print()
    
    print("Crank RPM Statistics:")
    print(f"  Minimum: {min_crank_rpm} RPM")
    print(f"  Maximum: {max_crank_rpm} RPM")
    print(f"  Average: {avg_crank_rpm:.1f} RPM")
    print()
    
    print("Wheel RPM Statistics:")
    print(f"  Minimum: {min_wheel_rpm} RPM")
    print(f"  Maximum: {max_wheel_rpm} RPM")
    print(f"  Average: {avg_wheel_rpm:.1f} RPM")
    print()
    
    print("=" * 60)
    print("Recommended Gear Ratio")
    print("=" * 60)
    print()
    print(f"Based on the data collected, the fixed gear ratio is:")
    print(f"  {avg_ratio:.4f} (average)")
    print()
    print(f"Or use the median for a more stable value:")
    print(f"  {median_ratio:.4f} (median)")
    print()
    print(f"Or use the mode (most common value):")
    print(f"  {mode_ratio:.4f} (mode)")
    print()
    
    if std_dev < 0.01:
        print("✓ Low standard deviation - ratio is very consistent!")
    elif std_dev < 0.05:
        print("✓ Good standard deviation - ratio is fairly consistent")
    else:
        print("⚠ High standard deviation - ratio varies significantly")
        print("  This may indicate:")
        print("  - Inconsistent pedaling speed")
        print("  - Sensor alignment issues")
        print("  - Mechanical issues with the bike trainer")
    print()
    
    # Show ratio distribution
    print("Ratio Distribution (rounded to 0.01):")
    print("-" * 60)
    sorted_bins = sorted(ratio_bins.items())
    for bin_ratio, count in sorted_bins[:20]:  # Show top 20 most common
        bar_length = int(count / len(ratios) * 40)
        bar = "█" * bar_length
        percentage = (count / len(ratios)) * 100
        print(f"  {bin_ratio:5.2f}: {bar} {count:4d} ({percentage:5.1f}%)")
    
    if len(sorted_bins) > 20:
        print(f"  ... and {len(sorted_bins) - 20} more bins")
    print()
    
    print("=" * 60)
    print("Usage in Code")
    print("=" * 60)
    print()
    print("To use this ratio in your code, you can calculate wheel RPM from crank RPM:")
    print(f"  wheel_rpm = crank_rpm * {avg_ratio:.4f}")
    print()
    print("Or if you want to verify the ratio matches your gear selector:")
    print(f"  expected_ratio = {avg_ratio:.4f}")
    print("  actual_ratio = wheel_rpm / crank_rpm")
    print("  if abs(actual_ratio - expected_ratio) > 0.1:")
    print("      print('Warning: Ratio mismatch!')")
    print()

print("Calculation complete!")
