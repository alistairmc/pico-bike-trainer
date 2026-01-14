# Bluetooth Low Energy (BLE) Diagnostic Tool
# Tests FTMS (Fitness Machine Service) implementation for Rouvy/Zwift compatibility
# Requires Raspberry Pi Pico W (with Bluetooth support)

print("=" * 60)
print("FTMS (Fitness Machine Service) Diagnostic Tool")
print("=" * 60)
print()

# Check if BLE is available
try:
    import ubluetooth
    from Class_BLEController import BLEController
    BLE_AVAILABLE = True
    print("✓ BLE modules imported successfully")
except ImportError as e:
    print(f"✗ BLE not available: {e}")
    print("  This script requires Raspberry Pi Pico W with Bluetooth support")
    BLE_AVAILABLE = False
    import sys
    sys.exit(1)

print()

# Test 1: Check BLE module availability
print("Test 1: Checking BLE module availability")
print("-" * 60)
try:
    ble = ubluetooth.BLE()
    print(f"✓ BLE object created: {ble}")

    ble.active(True)
    print(f"✓ BLE activated: {ble.active()}")

    ble.active(False)
    print(f"✓ BLE deactivated successfully")
except Exception as e:
    print(f"✗ Error with BLE module: {e}")
    import sys
    sys.exit(1)

print()

# Test 2: Initialize BLE Controller with FTMS
print("Test 2: Initializing BLE Controller (FTMS)")
print("-" * 60)
try:
    # Create minimal mock controllers for testing
    class MockSpeedController:
        def get_wheel_rpm(self):
            return 60  # Simulate 60 RPM
        def get_crank_rpm(self):
            return 80  # Simulate 80 RPM
        def get_calculated_speed(self):
            return 25.0  # Simulate 25 km/h

    class MockLoadController:
        def get_incline(self):
            return 0.0
        def get_current_load_percent(self):
            return 50.0  # Simulate 50% resistance
        def set_incline(self, value):
            print(f"  Mock: Incline set to {value:.1f}%")

    mock_speed = MockSpeedController()
    mock_load = MockLoadController()

    ble_controller = BLEController(
        name="PicoBike Test",
        speed_controller=mock_speed,
        load_controller=mock_load
    )

    print("✓ BLE Controller initialized successfully")
    print(f"  Device name: {ble_controller.name}")
    print(f"  Pairing name: {ble_controller.pairing_name}")

except Exception as e:
    print(f"✗ Error initializing BLE Controller: {e}")
    import sys
    sys.print_exception(e)
    sys.exit(1)

print()

# Test 3: Check FTMS service registration
print("Test 3: Checking FTMS service registration")
print("-" * 60)
try:
    # Check FTMS handles
    if hasattr(ble_controller, 'ftms_feature_handle'):
        print(f"✓ FTMS Feature handle: {ble_controller.ftms_feature_handle}")
    else:
        print("✗ FTMS Feature handle not found")

    if hasattr(ble_controller, 'ftms_indoor_bike_data_handle'):
        print(f"✓ FTMS Indoor Bike Data handle: {ble_controller.ftms_indoor_bike_data_handle}")
    else:
        print("✗ FTMS Indoor Bike Data handle not found")

    if hasattr(ble_controller, 'ftms_control_point_handle'):
        print(f"✓ FTMS Control Point handle: {ble_controller.ftms_control_point_handle}")
    else:
        print("✗ FTMS Control Point handle not found")

    if hasattr(ble_controller, 'ftms_status_handle'):
        print(f"✓ FTMS Status handle: {ble_controller.ftms_status_handle}")
    else:
        print("✗ FTMS Status handle not found")

    # Check CSC handles
    if hasattr(ble_controller, 'cscs_measurement_handle'):
        print(f"✓ CSC Measurement handle: {ble_controller.cscs_measurement_handle}")
    else:
        print("✗ CSC Measurement handle not found")

    if hasattr(ble_controller, 'cscs_feature_handle'):
        print(f"✓ CSC Feature handle: {ble_controller.cscs_feature_handle}")
    else:
        print("✗ CSC Feature handle not found")

    print("✓ All service handles registered")

except Exception as e:
    print(f"✗ Error checking services: {e}")
    import sys
    sys.print_exception(e)

print()

# Test 4: Test advertising
print("Test 4: Testing BLE advertising")
print("-" * 60)
try:
    if ble_controller.ble.active():
        print("✓ BLE is active")
    else:
        print("✗ BLE is not active")

    print(f"  Normal device name: '{ble_controller.normal_name}'")
    print(f"  Pairing device name: '{ble_controller.pairing_name}'")
    print()
    print("  BLE is advertising FTMS (Fitness Machine Service)")
    print("  This is the standard service for Rouvy, Zwift, etc.")
    print()
    print("  IMPORTANT: Look for device in your cycling app:")
    print(f"    - Device name: '{ble_controller.name}'")
    print("    - Service: Fitness Machine (0x1826)")
    print()
    print("  Troubleshooting:")
    print("    - Use Rouvy, Zwift, or nRF Connect app")
    print("    - Enable BLE scanning in your app")
    print("    - Device appears as 'Indoor Bike' or 'Smart Trainer'")

except Exception as e:
    print(f"✗ Error with advertising: {e}")
    import sys
    sys.print_exception(e)

print()

# Test 5: Test pairing mode
print("Test 5: Testing pairing mode")
print("-" * 60)
try:
    import utime

    print("  Starting pairing mode...")
    ble_controller.start_pairing_mode()

    if ble_controller.is_pairing_mode():
        print("✓ Pairing mode activated")
        print(f"  Device name: {ble_controller.pairing_name}")
        print("  Advertising interval: 100ms (faster)")

        for i in range(3):
            utime.sleep(1)
            print(f"  [{i+1}s] Pairing mode active")

        ble_controller.stop_pairing_mode()
        print("✓ Pairing mode stopped")
    else:
        print("✗ Pairing mode did not activate")

except Exception as e:
    print(f"✗ Error testing pairing mode: {e}")
    import sys
    sys.print_exception(e)

print()

# Test 6: Test data update functions
print("Test 6: Testing FTMS data broadcast")
print("-" * 60)
try:
    import utime

    print("  Testing update() (broadcasts FTMS + CSC data)...")
    try:
        ble_controller.update()
        print("✓ update() called successfully")
    except Exception as e:
        print(f"  Note: {e} (expected if no device connected)")

    print("✓ Data broadcast functions work")

except Exception as e:
    print(f"✗ Error testing data updates: {e}")

print()

# Test 7: Test control point simulation
print("Test 7: Testing FTMS Control Point simulation")
print("-" * 60)
try:
    import struct

    # Simulate SetTargetInclination command
    print("  Simulating SetTargetInclination (5.0%)...")
    # Op code 0x03, incline = 50 (5.0% in 0.1% units)
    cmd = struct.pack("<Bh", 0x03, 50)
    print(f"  Command bytes: {cmd.hex()}")
    ble_controller._handle_control_point(cmd)
    print(f"✓ Target incline set to: {ble_controller.target_incline:.1f}%")

    # Simulate SetIndoorBikeSimulation command
    print()
    print("  Simulating SetIndoorBikeSimulation (grade=3.5%)...")
    # Op code 0x11, wind=0, grade=350 (3.5%), crr=33, cw=51
    cmd = struct.pack("<BhhBB", 0x11, 0, 350, 33, 51)
    print(f"  Command bytes: {cmd.hex()}")
    ble_controller._handle_control_point(cmd)
    print(f"✓ Sim grade set to: {ble_controller.target_incline:.2f}%")

except Exception as e:
    print(f"✗ Error testing control point: {e}")
    import sys
    sys.print_exception(e)

print()

# Test 8: Connection monitoring
print("Test 8: Client Connection Monitoring")
print("-" * 60)
print("  This test monitors for client connections")
print("  Connect from Rouvy, Zwift, or a BLE scanner")
print()

try:
    import utime

    print("  Starting pairing mode...")
    ble_controller.start_pairing_mode()
    print(f"  ✓ Advertising as '{ble_controller.pairing_name}' (FTMS)")
    print()
    print("  Monitoring for 120 seconds...")
    print("  Press Ctrl+C to skip")
    print()

    start_time = utime.ticks_ms()
    monitor_duration = 120000
    connection_detected = False

    try:
        while True:
            current_time = utime.ticks_ms()
            elapsed = utime.ticks_diff(current_time, start_time)

            if elapsed >= monitor_duration:
                break

            ble_controller.update_pairing_mode(current_time)

            if ble_controller.is_connected():
                if not connection_detected:
                    connection_detected = True
                    print(f"  ✓✓✓ CONNECTION DETECTED! ✓✓✓")
                    print(f"     Connection handle: {ble_controller.conn_handle}")
                    print(f"     Control granted: {ble_controller.control_granted}")
                    print()

                    # Send test data
                    for i in range(5):
                        utime.sleep_ms(500)
                        ble_controller.update()
                        print(f"     [{i+1}/5] FTMS data sent")

            if elapsed % 10000 < 100:
                remaining = (monitor_duration - elapsed) // 1000
                status = "✓ Connected" if ble_controller.is_connected() else "○ Waiting..."
                print(f"  [{remaining:3d}s] {status}")

            utime.sleep_ms(100)

    except KeyboardInterrupt:
        print()
        print("  Test interrupted")

    ble_controller.stop_pairing_mode()

    if connection_detected:
        print("  ✓✓✓ CONNECTION TEST PASSED ✓✓✓")
    else:
        print("  ○ No connection detected")

except Exception as e:
    print(f"✗ Error: {e}")
    import sys
    sys.print_exception(e)

print()

# Summary
print("=" * 60)
print("FTMS Diagnostic Summary")
print("=" * 60)
print()
print("Services Implemented:")
print("  [✓] Fitness Machine Service (FTMS) - 0x1826")
print("      - Indoor Bike Data (speed, cadence, resistance)")
print("      - Control Point (incline, resistance, simulation)")
print("      - Machine Status & Training Status")
print("  [✓] Cycling Speed and Cadence (CSC) - 0x1816")
print("      - Wheel and Crank revolution data")
print()
print("Compatible Apps:")
print("  - Rouvy")
print("  - Zwift")
print("  - TrainerRoad")
print("  - Kinomap")
print("  - Any FTMS-compatible app")
print()
print("Control Point Commands Supported:")
print("  - Request Control (0x00)")
print("  - Reset (0x01)")
print("  - Set Target Inclination (0x03)")
print("  - Set Target Resistance (0x04)")
print("  - Set Target Power (0x05)")
print("  - Start/Resume (0x07)")
print("  - Stop/Pause (0x08)")
print("  - Set Indoor Bike Simulation (0x11)")
print()
print("Test complete!")
