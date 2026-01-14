# Button Diagnostic Tool
# This script tests if all buttons are working correctly
# Run this to diagnose button issues

from machine import Pin
import utime

print("=" * 60)
print("Button Diagnostic Tool")
print("=" * 60)
print()

# Button GPIO pin assignments
BUTTON_PINS = {
    2: "Increment Gear",
    3: "Decrement Gear",
    16: "Increase Incline",
    17: "Decrease Incline",
    18: "Control (Timer)"
}

# Initialize all button pins
buttons = {}
for pin_num, name in BUTTON_PINS.items():
    buttons[pin_num] = {
        'pin': Pin(pin_num, Pin.IN, Pin.PULL_UP),
        'name': name,
        'prev_state': 1,
        'press_count': 0,
        'release_count': 0,
        'last_press_time': 0,
        'last_release_time': 0
    }

print("Initializing buttons...")
for pin_num, button in buttons.items():
    state = button['pin'].value()
    print(f"GPIO {pin_num:2d} ({button['name']:20s}): {state} (0=PRESSED, 1=RELEASED)")
print()

# Test 1: Check initial button states
print("Test 1: Checking initial button states")
print("-" * 60)
for pin_num, button in buttons.items():
    state = button['pin'].value()
    status = "PRESSED" if state == 0 else "RELEASED"
    print(f"GPIO {pin_num:2d} ({button['name']:20s}): {status}")
print()
print("Note: With PULL_UP resistors, buttons should read 1 (RELEASED) when not pressed")
print("      and 0 (PRESSED) when pressed.")
print()

# Test 2: Monitor button presses for 30 seconds
print("Test 2: Monitoring button presses for 30 seconds")
print("-" * 60)
print("Press each button and watch for press/release detection")
print("Control button: Try short press and long press (3+ seconds)")
print()
print("Press Ctrl+C to stop early")
print()

start_time = utime.ticks_ms()
test_duration_ms = 30000  # 30 seconds
last_status_time = 0
status_interval_ms = 1000  # Print status every second

try:
    while utime.ticks_diff(utime.ticks_ms(), start_time) < test_duration_ms:
        current_time = utime.ticks_ms()
        
        # Check each button
        for pin_num, button in buttons.items():
            current_state = button['pin'].value()
            prev_state = button['prev_state']
            
            # Detect button press (transition from 1 to 0)
            if prev_state == 1 and current_state == 0:
                button['press_count'] += 1
                button['last_press_time'] = current_time
                elapsed = utime.ticks_diff(current_time, start_time) / 1000
                print(f"[{elapsed:6.1f}s] GPIO {pin_num:2d} ({button['name']:20s}): PRESSED")
            
            # Detect button release (transition from 0 to 1)
            elif prev_state == 0 and current_state == 1:
                button['release_count'] += 1
                button['last_release_time'] = current_time
                elapsed = utime.ticks_diff(current_time, start_time) / 1000
                
                # Calculate hold duration
                if button['last_press_time'] > 0:
                    hold_duration = utime.ticks_diff(current_time, button['last_press_time'])
                    hold_sec = hold_duration / 1000
                    
                    if hold_sec >= 3.0:
                        print(f"[{elapsed:6.1f}s] GPIO {pin_num:2d} ({button['name']:20s}): RELEASED (LONG PRESS: {hold_sec:.1f}s)")
                    else:
                        print(f"[{elapsed:6.1f}s] GPIO {pin_num:2d} ({button['name']:20s}): RELEASED (hold: {hold_sec:.2f}s)")
            
            button['prev_state'] = current_state
        
        # Print status every second
        if utime.ticks_diff(current_time, last_status_time) >= status_interval_ms:
            elapsed = utime.ticks_diff(current_time, start_time) / 1000
            remaining = (test_duration_ms / 1000) - elapsed
            print(f"[Status] Test running... {remaining:.0f}s remaining", end='\r')
            last_status_time = current_time
        
        utime.sleep_ms(10)  # Small delay to avoid tight loop
    
    print()  # New line after status updates
    print()
    
except KeyboardInterrupt:
    print()
    print("Test interrupted by user")
    print()

# Test 3: Summary statistics
print("Test 3: Summary Statistics")
print("-" * 60)
print(f"{'Button':<25} {'Presses':<10} {'Releases':<10} {'Status'}")
print("-" * 60)

for pin_num, button in sorted(buttons.items()):
    name = button['name']
    presses = button['press_count']
    releases = button['release_count']
    
    # Check if button is currently pressed
    current_state = button['pin'].value()
    if current_state == 0:
        status = "CURRENTLY PRESSED"
    elif presses == 0 and releases == 0:
        status = "NO ACTIVITY"
    elif presses == releases:
        status = "OK"
    else:
        status = f"MISMATCH (presses != releases)"
    
    print(f"{name:<25} {presses:<10} {releases:<10} {status}")

print()

# Test 4: Button state monitoring (real-time)
print("Test 4: Real-time button state monitoring")
print("-" * 60)
print("Press any button to see its state change")
print("Press Ctrl+C to exit")
print()
print(f"{'Time':<8} {'GPIO':<6} {'Button Name':<20} {'State':<10} {'Change'}")
print("-" * 60)

try:
    start_time = utime.ticks_ms()
    while True:
        current_time = utime.ticks_ms()
        elapsed = utime.ticks_diff(current_time, start_time) / 1000
        
        for pin_num, button in sorted(buttons.items()):
            current_state = button['pin'].value()
            prev_state = button['prev_state']
            
            if current_state != prev_state:
                state_str = "PRESSED" if current_state == 0 else "RELEASED"
                change_str = "PRESS" if current_state == 0 else "RELEASE"
                print(f"{elapsed:7.2f}s  {pin_num:<6} {button['name']:<20} {state_str:<10} {change_str}")
                button['prev_state'] = current_state
        
        utime.sleep_ms(50)  # Check every 50ms
        
except KeyboardInterrupt:
    print()
    print("Test complete!")
    print()

# Final diagnostics
print("=" * 60)
print("Diagnostic Summary")
print("=" * 60)
print()

all_working = True
for pin_num, button in sorted(buttons.items()):
    presses = button['press_count']
    releases = button['release_count']
    current_state = button['pin'].value()
    
    if presses == 0 and releases == 0:
        print(f"⚠️  GPIO {pin_num:2d} ({button['name']:20s}): NO ACTIVITY DETECTED")
        print(f"   - Check wiring and connections")
        print(f"   - Verify button is properly connected to GPIO {pin_num}")
        print(f"   - Check if button uses pull-up resistor (should read 1 when released)")
        all_working = False
    elif presses != releases:
        print(f"⚠️  GPIO {pin_num:2d} ({button['name']:20s}): PRESS/RELEASE MISMATCH")
        print(f"   - Presses: {presses}, Releases: {releases}")
        print(f"   - Button may be bouncing or connection is loose")
        all_working = False
    elif current_state == 0:
        print(f"⚠️  GPIO {pin_num:2d} ({button['name']:20s}): STUCK PRESSED")
        print(f"   - Button may be stuck or wiring issue")
        all_working = False
    else:
        print(f"✓  GPIO {pin_num:2d} ({button['name']:20s}): WORKING ({presses} presses detected)")

print()
if all_working:
    print("All buttons appear to be working correctly!")
else:
    print("Some buttons may have issues. Check the warnings above.")
print()
