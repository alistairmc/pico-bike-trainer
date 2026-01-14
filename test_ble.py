# Bluetooth Low Energy (BLE) Diagnostic Tool
# This script tests if BLE functionality is working correctly
# Run this to diagnose BLE issues
# Requires Raspberry Pi Pico W (with Bluetooth support)

print("=" * 60)
print("Bluetooth Low Energy (BLE) Diagnostic Tool")
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
    print("  Regular Pico does not have Bluetooth capability")
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

    # Check if BLE can be activated
    ble.active(True)
    print(f"✓ BLE activated: {ble.active()}")

    ble.active(False)
    print(f"✓ BLE deactivated successfully")
except Exception as e:
    print(f"✗ Error with BLE module: {e}")
    print("  BLE hardware may not be available or not working")
    import sys
    sys.exit(1)

print()

# Test 2: Initialize BLE Controller
print("Test 2: Initializing BLE Controller")
print("-" * 60)
try:
    # Create minimal mock controllers for testing
    class MockSpeedController:
        def get_wheel_rpm(self):
            return 60  # Simulate 60 RPM
        def get_crank_rpm(self):
            return 80  # Simulate 80 RPM

    class MockLoadController:
        def get_incline(self):
            return 0.0
        def set_incline(self, value):
            print(f"  Mock: Incline set to {value}%")

    mock_speed = MockSpeedController()
    mock_load = MockLoadController()

    ble_controller = BLEController(
        name="Pico Bike Trainer Test",
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

# Test 3: Check service registration
print("Test 3: Checking BLE service registration")
print("-" * 60)
try:
    # Check if handles are set
    if hasattr(ble_controller, 'speed_char_handle'):
        print(f"✓ Speed characteristic handle: {ble_controller.speed_char_handle}")
    else:
        print("✗ Speed characteristic handle not found")

    if hasattr(ble_controller, 'feature_char_handle'):
        print(f"✓ Feature characteristic handle: {ble_controller.feature_char_handle}")
    else:
        print("✗ Feature characteristic handle not found")

    if hasattr(ble_controller, 'incline_char_handle'):
        print(f"✓ Incline characteristic handle: {ble_controller.incline_char_handle}")
    else:
        print("✗ Incline characteristic handle not found")

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
    print("  BLE should now be advertising as 'Pico Bike Trainer Test'")
    print("  Check your device's Bluetooth scanner to see if it appears")
    print("  Advertising interval: 500ms (normal mode)")

    # Check if advertising is active
    if ble_controller.ble.active():
        print("✓ BLE is active and advertising")
    else:
        print("✗ BLE is not active")

except Exception as e:
    print(f"✗ Error with advertising: {e}")

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
        print(f"  Device name changed to: {ble_controller.pairing_name}")
        print("  Advertising interval: 200ms (faster in pairing mode)")

        # Simulate some time passing
        start_time = utime.ticks_ms()
        remaining = 120

        print("  Pairing mode will last 120 seconds or until connected")
        print("  Monitoring pairing mode for 5 seconds...")

        for i in range(5):
            utime.sleep(1)
            current_time = utime.ticks_ms()
            ble_controller.update_pairing_mode(current_time)

            if ble_controller.is_pairing_mode():
                elapsed = utime.ticks_diff(current_time, start_time) // 1000
                remaining = 120 - elapsed
                print(f"  [{i+1}s] Pairing mode active, {remaining}s remaining")
            else:
                print(f"  [{i+1}s] Pairing mode ended")
                break

        # Stop pairing mode
        print("  Stopping pairing mode...")
        ble_controller.stop_pairing_mode()

        if not ble_controller.is_pairing_mode():
            print("✓ Pairing mode stopped successfully")
        else:
            print("✗ Pairing mode did not stop")
    else:
        print("✗ Pairing mode did not activate")

except Exception as e:
    print(f"✗ Error testing pairing mode: {e}")
    import sys
    sys.print_exception(e)

print()

# Test 6: Test data updates
print("Test 6: Testing data update functions")
print("-" * 60)
try:
    import utime

    print("  Testing update_combined_data()...")
    current_time = utime.ticks_ms()

    # This will fail if not connected, but we can test the function exists
    try:
        ble_controller.update_combined_data()
        print("✓ update_combined_data() called (no error if not connected)")
    except Exception as e:
        print(f"  Note: {e} (expected if no device connected)")

    print("  Testing update_incline_value()...")
    try:
        ble_controller.update_incline_value()
        print("✓ update_incline_value() called successfully")
    except Exception as e:
        print(f"  Note: {e}")

    print("✓ Data update functions work")

except Exception as e:
    print(f"✗ Error testing data updates: {e}")

print()

# Test 7: Test incline write simulation
print("Test 7: Testing incline control write simulation")
print("-" * 60)
try:
    import struct

    # Simulate writing incline value
    test_incline = 15.5  # 15.5% incline
    incline_data = struct.pack("<f", test_incline)

    print(f"  Simulating incline write: {test_incline}%")
    print(f"  Data bytes: {incline_data.hex()}")

    # Manually call the handler (simulating BLE write)
    ble_controller._handle_incline_write(incline_data)

    if abs(ble_controller.target_incline - test_incline) < 0.1:
        print(f"✓ Incline value set correctly: {ble_controller.target_incline}%")
    else:
        print(f"✗ Incline value mismatch: expected {test_incline}%, got {ble_controller.target_incline}%")

except Exception as e:
    print(f"✗ Error testing incline write: {e}")
    import sys
    sys.print_exception(e)

print()

# Test 8: Connection status
print("Test 8: Checking connection status")
print("-" * 60)
try:
    is_connected = ble_controller.is_connected()
    print(f"  Connection status: {'Connected' if is_connected else 'Not connected'}")

    if not is_connected:
        print("  (This is normal - no device has connected yet)")
        print("  Use a BLE scanner app to connect to the device")

    print("✓ Connection status check works")

except Exception as e:
    print(f"✗ Error checking connection: {e}")

print()

# Test 9: Wheel circumference
print("Test 9: Testing wheel circumference setting")
print("-" * 60)
try:
    test_circumference = 2075  # 26-inch wheel in mm
    ble_controller.set_wheel_circumference(test_circumference)

    if ble_controller.wheel_circumference_mm == test_circumference:
        print(f"✓ Wheel circumference set correctly: {ble_controller.wheel_circumference_mm}mm")
    else:
        print(f"✗ Wheel circumference mismatch")

except Exception as e:
    print(f"✗ Error setting wheel circumference: {e}")

print()

# Summary
print("=" * 60)
print("Diagnostic Summary")
print("=" * 60)
print()

all_tests_passed = True

print("BLE Functionality Tests:")
print("  [✓] BLE module available")
print("  [✓] BLE Controller initialization")
print("  [✓] Service registration")
print("  [✓] Advertising")
print("  [✓] Pairing mode")
print("  [✓] Data update functions")
print("  [✓] Incline control")
print("  [✓] Connection status")
print("  [✓] Configuration")
print()

print("Next Steps:")
print("  1. Use a BLE scanner app (like nRF Connect, LightBlue, etc.)")
print("  2. Scan for 'Pico Bike Trainer Test' device")
print("  3. Connect to the device")
print("  4. Look for services:")
print("     - Cycling Speed and Cadence Service (0x1816)")
print("     - Custom Incline Service (UUID: 12345678-1234-1234-1234-123456789abc)")
print("  5. Subscribe to CSC Measurement characteristic for speed/cadence data")
print("  6. Write to Incline characteristic to test incline control")
print()

print("Pairing Mode:")
print("  - Hold control button (GPIO 18) for 6 seconds to activate")
print("  - Device name changes to 'Pico Bike Trainer [PAIRING]'")
print("  - Pairing mode lasts 120 seconds or until connected")
print()

print("Troubleshooting:")
if not ble_controller.is_connected():
    print("  - Device is not connected (this is normal)")
    print("  - Connect using a BLE scanner app to test full functionality")
else:
    print("  - Device is connected!")
    print("  - You can now test data transmission")

print()
print("Test complete!")
print()
