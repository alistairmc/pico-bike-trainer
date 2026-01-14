# Pico Bike Trainer

A Raspberry Pi Pico W-based smart bike trainer system that provides realistic resistance simulation based on gear selection and incline settings. The system uses hall sensors to measure speed and motor position, controls resistance through an L298N motor controller, and broadcasts data via Bluetooth Low Energy (BLE) for compatibility with cycling apps like **Rouvy**, **Zwift**, and **TrainerRoad**.

## Table of Contents

- [Overview](#overview)
- [Bluetooth Connectivity](#bluetooth-connectivity)
- [GPIO Pin Assignments](#gpio-pin-assignments)
- [System Architecture](#system-architecture)
- [Components](#components)
- [Features](#features)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Technical Details](#technical-details)

## Overview

The Pico Bike Trainer is a smart bike trainer system that:
- Measures bike speed using a hall sensor
- Tracks motor crank position for load control
- Adjusts resistance based on gear selection (1-7 gears)
- Simulates incline/decline (-100% to +100%)
- Displays real-time metrics on a 240x240 LCD screen
- Controls resistance using an L298N motor controller
- **Broadcasts via Bluetooth** for use with cycling apps (Rouvy, Zwift, etc.)
- **Receives incline commands** from apps for realistic hill simulation

## Bluetooth Connectivity

### Overview

The Pico Bike Trainer implements the **Fitness Machine Service (FTMS)** - the standard Bluetooth protocol used by smart trainers. This allows the trainer to work with popular cycling apps.

### Compatible Apps

| App | Features |
|-----|----------|
| **Rouvy** | Full support - speed, cadence, resistance control, hill simulation |
| **Zwift** | Full support - speed, cadence, power display, ERG mode |
| **TrainerRoad** | Full support - structured workouts, ERG mode |
| **Kinomap** | Full support - video routes, resistance control |
| **Any FTMS app** | Standard FTMS protocol compatibility |

### BLE Services Implemented

| Service | UUID | Description |
|---------|------|-------------|
| **Fitness Machine (FTMS)** | 0x1826 | Primary smart trainer service |
| **Cycling Speed & Cadence (CSC)** | 0x1816 | Basic speed/cadence for simple apps |

### FTMS Characteristics

| Characteristic | UUID | Function |
|----------------|------|----------|
| Feature | 0x2ACC | Advertises trainer capabilities |
| Indoor Bike Data | 0x2AD2 | Broadcasts speed, cadence, resistance |
| Control Point | 0x2AD9 | Receives commands from apps |
| Machine Status | 0x2ADA | Notifies status changes |
| Training Status | 0x2AD3 | Current workout state |
| Resistance Range | 0x2AD6 | 1-100% supported |
| Inclination Range | 0x2AD5 | -20% to +20% supported |

### Supported Control Commands

When connected to an app like Rouvy, the trainer responds to these commands:

| Command | Op Code | Description |
|---------|---------|-------------|
| Request Control | 0x00 | App requests control of trainer |
| Reset | 0x01 | Reset trainer to default state |
| Set Target Inclination | 0x03 | Set hill grade (-20% to +20%) |
| Set Target Resistance | 0x04 | Set resistance level (0-100%) |
| Set Target Power | 0x05 | ERG mode - target wattage |
| Start/Resume | 0x07 | Start workout |
| Stop/Pause | 0x08 | Pause workout |
| **Indoor Bike Simulation** | 0x11 | **Hill simulation with grade, wind, etc.** |

### Pairing Mode

To connect the trainer to an app:

1. **Hold Control Button (GPIO 18) for 6 seconds** to enter pairing mode
2. The display shows "BLE PAIRING" with a countdown (120 seconds)
3. Open your cycling app and scan for sensors
4. Look for device named **"PicoBike PAIR"**
5. Connect to the trainer
6. Pairing mode ends automatically when connected

### Indoor Bike Simulation (How Rouvy Works)

When riding a route in Rouvy, the app sends **Indoor Bike Simulation Parameters** (Op Code 0x11):

```
Parameters:
- Wind Speed: Head/tail wind in m/s
- Grade: Hill grade in 0.01% units (e.g., 350 = 3.5% climb)
- Rolling Resistance Coefficient (CRR)
- Wind Resistance Coefficient (CW)
```

The trainer extracts the **grade** value and adjusts resistance accordingly, simulating the feel of climbing or descending.

## GPIO Pin Assignments

### Motor Control
| GPIO | Function | Direction | Description |
|------|----------|-----------|-------------|
| **0** | Motor Count Sensor | INPUT | Hall sensor for counting motor rotations (rising edge interrupt) |
| **1** | Motor Stop Trigger | INPUT | Detects when motor crank is at bottom position (0°, least resistance) |
| **5** | L298N IN1 | OUTPUT | Motor direction control (forward when HIGH) |
| **6** | L298N IN2 | OUTPUT | Motor direction control (reverse when HIGH) |

### Speed Sensors
| GPIO | Function | Direction | Description |
|------|----------|-----------|-------------|
| **4** | Wheel Speed Hall Sensor | INPUT | Hall sensor for measuring flywheel/wheel speed (rising edge interrupt) |
| **7** | Crank Hall Sensor | INPUT | Hall sensor for measuring crank/pedal speed (rising edge interrupt) |

### Display (LCD 1.3" 240x240)
| GPIO | Function | Direction | Description |
|------|----------|-----------|-------------|
| **8** | LCD DC | OUTPUT | Data/Command select pin |
| **9** | LCD CS | OUTPUT | Chip select (SPI) |
| **10** | LCD SCK | OUTPUT | SPI clock |
| **11** | LCD MOSI | OUTPUT | SPI data (Master Out Slave In) |
| **12** | LCD RST | OUTPUT | Reset pin |
| **13** | LCD BL | OUTPUT | Backlight PWM control |

### User Input (Buttons/Joystick)
| GPIO | Function | Direction | Description |
|------|----------|-----------|-------------|
| **2** | Increment Gear | INPUT | Increment gear (PULL_UP) |
| **3** | Decrement Gear | INPUT | Decrement gear (PULL_UP) |
| **16** | Increase Incline | INPUT | Increase incline/uphill (PULL_UP) |
| **17** | Decrease Incline | INPUT | Decrease incline/downhill (PULL_UP) |
| **18** | Control Button | INPUT | Timer & BLE control (PULL_UP) - see below |

### Control Button (GPIO 18) Functions
| Press Duration | Action |
|----------------|--------|
| Short press | Start/pause timer |
| 3 second hold | Reset timer (when paused) |
| 6 second hold | Enter BLE pairing mode (120 seconds) |

### GPIO Summary
- **Total GPIO Pins Used**: 18
- **Input Pins**: 10 (all with PULL_UP)
  - Motor sensors: 0, 1
  - Speed sensors: 4, 7
  - Buttons: 2, 3, 16, 17, 18
- **Output Pins**: 8
  - Motor control: 5, 6
  - Display: 8, 9, 10, 11, 12, 13
- **SPI Bus**: SPI1 (pins 10, 11)
- **PWM**: Pin 13 (backlight)

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi Pico                         │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ CrankSensor  │  │WheelSpeed    │  │ MotorSensor   │     │
│  │  (GPIO 7)    │  │Sensor(GPIO 4)│  │ (GPIO 0, 1)   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │               │
│         └────────┬────────┴──────────────────┘              │
│                  │                  │                         │
│         ┌────────▼─────────┐      │                         │
│         │ SpeedController    │      │                         │
│         │(RPM→Speed Conv)    │      │                         │
│         └────────┬───────────┘      │                         │
│                  │                  │                         │
│         ┌────────▼──────────┐  ┌───▼──────────┐              │
│         │   GearSelector    │  │LoadController│              │
│         └────────┬───────────┘  │  (GPIO 5, 6) │              │
│                  │              └──────────────┘              │
│                  │                                            │
│         ┌────────▼──────────────────┐                         │
│         │        View              │                         │
│         │  (Display Rendering)      │                         │
│         └────────┬─────────────────┘                         │
│                  │                                            │
│         ┌────────▼────────┐                                   │
│         │  LCD Display    │                                   │
│         │  (GPIO 8-13)    │                                   │
│         └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. CrankSensor (`Class_CrankSensor.py`)
- **Purpose**: Measures crank/pedal RPM using a hall sensor
- **GPIO**: Pin 7 (rising edge interrupt)
- **Features**:
  - Returns crank RPM only (no speed calculation)
  - One pulse = one full crank rotation (360 degrees)
  - Speed calculations handled by SpeedController

### 2. WheelSpeedSensor (`Class_WheelSpeedSensor.py`)
- **Purpose**: Measures flywheel/wheel RPM directly using a hall sensor
- **GPIO**: Pin 4 (rising edge interrupt)
- **Features**:
  - Returns wheel RPM only (no speed calculation)
  - One pulse = one full wheel revolution (360 degrees)
  - Independent measurement from crank sensor
  - Speed calculations handled by SpeedController

### 3. SpeedController (`Class_SpeedController.py`)
- **Purpose**: Manages all speed calculations
- **GPIO**: None (software controller)
- **Features**:
  - Converts RPM to speed in mph
  - Always displays speed in mph (miles per hour)
  - Handles wheel circumference and calibration
  - Calculates wheel RPM from crank RPM and gear ratio (if wheel sensor not available)
  - Provides speed and RPM data to View class for display
  - No display logic (handled by View class)

### 4. MotorSensor (`Class_MotorSensor.py`)
- **Purpose**: Tracks motor rotations and motor crank position
- **GPIO**: 
  - Pin 0: Motor rotation counter (rising edge interrupt)
  - Pin 1: Motor stop trigger (rising edge interrupt)
- **Features**:
  - Counts motor rotations (1000 rotations = 1 full motor crank rotation)
  - Tracks motor crank position (-500 to +500, representing 0° to 180°)
  - Position 0 = 0% load (stop position, least resistance)
  - Position ±500 = 100% load (180°, most resistance)
  - Supports forward and reverse direction tracking

### 5. LoadController (`Class_LoadController.py`)
- **Purpose**: Controls resistance by adjusting motor crank position
- **GPIO**: 
  - Pin 5: L298N IN1 (forward direction)
  - Pin 6: L298N IN2 (reverse direction)
- **Features**:
  - Adjusts load based on gear (25-75% base load)
  - Adjusts load based on incline (-25% to +25% adjustment)
  - Total load range: 0-100% in 5% increments
  - Startup calibration: moves to stop position (0°)
  - Always moves in correct direction (never increases load when decreasing, or vice versa)
  - Chooses shortest path when possible

### 6. GearSelector (`Class_GearSelector.py`)
- **Purpose**: Manages gear selection (1-7 gears)
- **GPIO**: None (software-based)
- **Features**:
  - 7 gears with ratio range 1.0 to 4.5
  - First gear = lowest ratio = 50% base load
  - Higher gears = higher base load (up to 75%)
  - Provides gear data to View class for display
  - No display logic (handled by View class)

### 7. ButtonController (`Class_ButtonController.py`)
- **Purpose**: Manages all button inputs and actions
- **GPIO**: Pins 2, 3, 16, 17, 18 (button inputs)
- **Features**:
  - Handles all button reading and debouncing
  - Dispatches actions to appropriate controllers
  - Separates input handling from business logic (MVC pattern)
  - Button functions:
    - GPIO 2: Increment gear
    - GPIO 3: Decrement gear
    - GPIO 16: Increase incline (uphill)
    - GPIO 17: Decrease incline (downhill)
    - GPIO 18: Control button (currently unused)

### 8. View (`Class_View.py`)
- **Purpose**: Centralized display rendering and presentation logic
- **GPIO**: None (uses LCD driver)
- **Features**:
  - Handles all display rendering operations
  - Separates presentation from business logic
  - Renders calculated speed (wheel RPM × gear ratio), wheel RPM, load, and incline
  - Renders gear selector display
  - Updates display at 4 Hz (250ms intervals)
  - Single source of truth for all display operations

### 9. LCD Display (`Class_LCD1Inch3.py`)
- **Purpose**: 240x240 pixel LCD display driver
- **GPIO**: Pins 8-13 (SPI communication)
- **Features**:
  - RGB565 color format
  - SPI communication at 100MHz
  - PWM backlight control
  - FrameBuffer-based drawing

### 10. BLEController (`Class_BLEController.py`)
- **Purpose**: Bluetooth Low Energy communication for cycling apps
- **GPIO**: None (uses Pico W wireless hardware)
- **Features**:
  - Implements FTMS (Fitness Machine Service) - UUID 0x1826
  - Implements CSC (Cycling Speed and Cadence) - UUID 0x1816
  - Broadcasts Indoor Bike Data (speed, cadence, resistance)
  - Receives control commands from apps (incline, resistance, ERG mode)
  - Supports Indoor Bike Simulation for realistic hill feel
  - Pairing mode with 120-second timeout
  - Compatible with Rouvy, Zwift, TrainerRoad, etc.

### 11. TimerController (`Class_TimerController.py`)
- **Purpose**: Workout timer/stopwatch functionality
- **GPIO**: None (software controller)
- **Features**:
  - Start/pause/resume timer
  - Reset timer (when paused)
  - Formats time as MM:SS
  - Displayed on LCD above gear selector

## Features

### Load Control
- **Base Load**: Determined by gear selection
  - First gear: 50% load (90° from stop)
  - Higher gears: 50-75% load (increasing with gear ratio)
- **Incline Adjustment**: ±25% from base load
  - Uphill: Increases load
  - Downhill: Decreases load
- **Total Load Range**: 0-100% in 5% increments
- **Position Control**: 
  - Position 0 = 0% load (stop position, least resistance)
  - Position ±500 = 100% load (180°, most resistance)
  - Both +500 and -500 represent the same load

### Speed Measurement
- **Crank Sensor**: Returns crank RPM (pedal/crank speed) - GPIO 7
- **Wheel Sensor**: Returns wheel RPM (flywheel/wheel speed) - GPIO 4
- **SpeedController**: Converts RPM to speed in mph
  - Calculates speed from wheel RPM multiplied by virtual gear ratio
  - Always displays speed in mph (miles per hour)
  - Manages calibration and wheel circumference
- **Calculated Speed**: Wheel RPM × Gear Ratio, converted to mph
- Wheel RPM (WRPM) displayed
- Configurable wheel circumference

### Display
- **View Class**: Centralized display rendering (Model-View-Controller pattern)
- Real-time calculated speed display (wheel RPM × gear ratio) in mph
- Current gear display
- Workout timer display (MM:SS format)
- Incline percentage display
- BLE pairing status display
- 4 Hz update rate (250ms intervals)
- All display logic separated from business logic

### User Controls
- **Gear Selection**: Increment/Decrement gear buttons (GPIO 2/3)
- **Incline Control**: Increase/Decrease incline buttons (GPIO 16/17, ±5% per press)
- **Timer Control**: Control button short press to start/pause (GPIO 18)
- **Timer Reset**: Control button 3-second hold to reset (when paused)
- **BLE Pairing**: Control button 6-second hold to enter pairing mode

### Bluetooth Connectivity
- **FTMS Service**: Full Fitness Machine Service implementation
- **CSC Service**: Cycling Speed and Cadence for basic apps
- **Indoor Bike Data**: Broadcasts speed, cadence, resistance
- **Control Point**: Receives commands from apps
- **Hill Simulation**: Responds to grade changes from Rouvy/Zwift
- **Pairing Mode**: 120-second discoverable mode for easy connection

### Timer
- **Workout Timer**: Stopwatch functionality for tracking workout duration
- **States**: Stopped, Running, Paused
- **Display**: Shows MM:SS format above gear selector
- **Controls**: Start/pause (short press), Reset (3-sec hold when paused)

## Hardware Requirements

### Required Components
1. **Raspberry Pi Pico W** (required for Bluetooth - regular Pico does not have BLE)
2. **LCD Display**: 1.3" 240x240 SPI LCD
3. **L298N Motor Driver**: For controlling resistance motor
4. **Hall Sensors**: 
   - Motor rotation sensor (GPIO 0)
   - Motor stop trigger (GPIO 1)
   - Crank sensor (GPIO 7)
   - Wheel speed sensor (GPIO 4)
5. **Buttons/Joystick**: For user input
6. **Resistance Motor**: Controlled by L298N

> **Note**: The Raspberry Pi **Pico W** is required for Bluetooth connectivity. The regular Pico does not have wireless capabilities. Without a Pico W, the trainer will still function but without BLE support for cycling apps.

### Motor Specifications
- **Motor Rotations per Crank Rotation**: 1000:1 ratio
- **Position Range**: -500 to +500 (representing 0° to 180°)
- **Stop Position**: 0 (bottom of motor crank, least resistance)
- **Max Load Position**: ±500 (180° from stop, most resistance)

## Installation

1. **Clone or download this repository**

2. **Upload files to Raspberry Pi Pico**:
   
   **Important:** When uploading files to the Pico, exclude the following:
   - Files starting with a dot (`.`) - hidden files like `.git`, `.vscode`, `.DS_Store`, etc.
   - Documentation files (`.md` files except `README.md`)
   - Test files (`test_*.py`)
   - IDE/editor files (`.code-workspace`, `.vscode/`, `.idea/`)
   - Build/cache files (`__pycache__/`, `.mypy_cache/`, etc.)
   - CMake files (`*.cmake`, `pico_sdk_import.cmake`)
   - License file (`LICENSE`)
   
   **Upload Tools:**
   - **Thonny IDE**: Automatically uses `.thonnyignore` file (already created)
   - **PyMakr/rshell**: Can use `.picoignore` file (already created)
   - **Manual upload**: Only upload `.py` files and `main.py`
   
   **Files to upload:**
   - `main.py` (required)
   - `Class_*.py` (all class files)
   - `README.md` (optional, for reference)

3. **Hardware Connections**:
   - Connect LCD display to GPIO pins 8-13
   - Connect motor sensors to GPIO pins 0, 1
   - Connect crank sensor to GPIO pin 7
   - Connect wheel speed sensor to GPIO pin 4
   - Connect L298N to GPIO pins 5, 6
   - Connect buttons to GPIO pins 2, 3, 16, 17, 18

4. **Power On**:
   - The system will automatically calibrate on startup
   - Motor will move to stop position (0°)
   - Display will show speed and gear information

## Usage

### Startup Sequence
1. System initializes all sensors and displays
2. Motor performs startup calibration:
   - Moves to stop position (0°)
   - Resets position counter
   - Ready for operation

### Normal Operation
- **Speed**: Automatically calculated from hall sensor
- **Gear Changes**: Use gear increment/decrement buttons (GPIO 2/3)
- **Incline Adjustment**: Use incline up/down buttons (GPIO 16/17)
- **Load**: Automatically adjusted based on gear and incline
- **Timer**: Control button (GPIO 18) to start/pause, 3-sec hold to reset

### Connecting to Cycling Apps (Rouvy, Zwift, etc.)
1. **Enter Pairing Mode**: Hold control button (GPIO 18) for 6 seconds
2. **Display Shows**: "BLE PAIRING" with countdown timer
3. **Open App**: Launch Rouvy, Zwift, or other FTMS-compatible app
4. **Scan for Sensors**: In the app, search for trainers/sensors
5. **Connect**: Select "PicoBike PAIR" from the device list
6. **Start Riding**: The app will now control resistance based on the route

### Display Information
- **Speed**: Calculated speed (wheel RPM × gear ratio) in mph
- **Timer**: Workout timer (MM:SS format) - above gear selector
- **Gear**: Current gear (1-7) - graphical selector
- **Incline**: Current incline percentage (-20% to +20%)
- **BLE Status**: Shows "BLE PAIRING" when in pairing mode

## Configuration

### Speed Calibration
The system is pre-configured for a 26-inch wheel:
```python
# Speed controller manages all calibration
speed_controller.set_wheel_circumference(2.075)  # 26-inch wheel in meters
speed_controller.set_calibration_from_wheel_rpm(48.28, 388)  # 30 mph at 388 RPM
```

To change wheel size, modify in `main.py`:
```python
speed_controller.set_wheel_circumference(circumference_in_meters)
```

### Gear Configuration
Default: 7 gears with ratio range 1.0 to 4.5
```python
gear_selector = GearSelector(num_gears=7, min_ratio=1.0, max_ratio=4.5)
```

### Load Configuration
- **Base Load Factor**: Default 1.0 (modify in `LoadController` initialization)
- **Load Increments**: 5% (hardcoded in `_update_load()`)
- **Motor Run Time**: 100ms default (adjustable in `LoadController`)

## Technical Details

### Motor Position System
- **Position 0**: Stop position (0% load, least resistance)
- **Position +500**: 180° forward (100% load, most resistance)
- **Position -500**: 180° reverse (100% load, most resistance)
- **Load Calculation**: `load = abs(position) / 500 * 100%`

### Interrupt Handlers
- **Motor Count**: Rising edge interrupt on GPIO 0
- **Motor Stop**: Rising edge interrupt on GPIO 1
- **Crank Sensor**: Rising edge interrupt on GPIO 7
- **Wheel Speed Sensor**: Rising edge interrupt on GPIO 4

### Display Update Rate
- **Fixed Rate**: 4 times per second (250ms intervals)
- **On-Demand**: Immediate update on button presses

### Load Calculation Formula
```
Base Load = 50% + (normalized_gear_ratio * 25%)
Incline Adjustment = (incline_percent / 100) * 25%
Total Load = Base Load + Incline Adjustment
Total Load = clamp(Total Load, 0%, 100%)
Total Load = round(Total Load / 5%) * 5%  // Quantize to 5% increments
```

### Motor Control Logic
- **Increasing Load**: Always moves forward (positive direction)
- **Decreasing Load**: Always moves reverse (negative direction)
- **Position Tracking**: Uses absolute position for load calculation
- **Direction Selection**: Prevents moving in wrong direction first

## Troubleshooting

### Motor Not Moving
- Check L298N connections (GPIO 5, 6)
- Verify motor power supply
- Check motor sensor connections (GPIO 0, 1)

### Speed Not Reading
- **Crank Sensor**: Verify hall sensor connection (GPIO 7)
- **Wheel Speed Sensor**: Verify hall sensor connection (GPIO 4)
- Check sensor alignment
- Verify interrupt handlers are active
- Ensure sensors are properly grounded

### Display Not Working
- Check SPI connections (GPIO 8-13)
- Verify backlight PWM (GPIO 13)
- Check power supply to display

### Load Not Adjusting
- Verify motor sensor is working (GPIO 0, 1)
- Check L298N motor control
- Ensure startup calibration completed successfully

### Bluetooth Not Working
- **Device not appearing in app**:
  - Ensure you're using a **Pico W** (regular Pico has no Bluetooth)
  - Enter pairing mode (hold control button for 6 seconds)
  - Look for device name "PicoBike PAIR"
  - Make sure you're using an FTMS-compatible app
  - Try restarting the Pico and the app

- **App not showing trainer**:
  - Ensure app is searching for "Trainers" or "Smart Trainers" (not just sensors)
  - Some apps need location services enabled for BLE scanning
  - Try the nRF Connect app to verify BLE is broadcasting

- **Connection drops**:
  - Stay within Bluetooth range (~10 meters)
  - Reduce interference from other devices
  - Check that the main loop is running (display updating)

- **Resistance not changing with hills**:
  - Verify the app is sending FTMS commands (check console output)
  - Ensure control is granted (app sends RequestControl first)
  - Check that load_controller is properly connected to BLE controller

### Timer Not Working
- **Timer not starting**: Press control button briefly (GPIO 18)
- **Timer not resetting**: Must be paused first, then hold for 3 seconds
- **Timer not displaying**: Check View class is receiving timer_controller

## Credits & Acknowledgments

### SmartSpin2k Project

The Bluetooth FTMS (Fitness Machine Service) implementation in this project is based on and inspired by the **SmartSpin2k** project:

- **Project**: [SmartSpin2k](https://github.com/doudar/SmartSpin2k)
- **Authors**: Anthony Doud & Joel Baranick
- **License**: GPL-2.0 (GNU General Public License v2)

The following code patterns and definitions were adapted from SmartSpin2k:
- FTMS flag definitions and constants
- Control Point command handling
- Indoor Bike Data packet structure
- FTMS characteristic UUIDs and service structure

SmartSpin2k is an excellent open-source project that transforms spin bikes into smart trainers. If you're looking for an ESP32-based solution with more features (power meter support, ERG mode, companion app), check out their project!

### Bluetooth Specifications

The FTMS implementation follows the official Bluetooth SIG specification:
- [Fitness Machine Service 1.0](https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/)

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

See the [LICENSE](LICENSE) file for the full license text.

### Third-Party Code Attribution

The file `Class_BLEController.py` contains code adapted from the **SmartSpin2k** project, which is licensed under GPL-2.0. Per GPL compatibility rules, this code is incorporated under the GPL-3.0 license of this project with the following attribution:

```
Original SmartSpin2k FTMS implementation:
Copyright (C) 2020 Anthony Doud & Joel Baranick
https://github.com/doudar/SmartSpin2k
Original License: GPL-2.0-only
```

## Author

Alistair Mcgranaghan - Initial work (24/09/2022)

## Architecture Notes

### Model-View-Controller (MVC) Pattern
The codebase follows an MVC architecture:
- **Models/Sensors**: Provide data (RPM, counts, position) - `CrankSensor`, `WheelSpeedSensor`, `MotorSensor`
- **Controllers**: Handle business logic (speed calculations, load control, gear selection) - `SpeedController`, `LoadController`, `GearSelector`
- **View**: Handles all display rendering - `View` class

### Separation of Concerns
- **Sensors**: Only return raw data (RPM, counts)
- **Controllers**: Process data and perform calculations
- **View**: Renders all display elements
- No display logic in sensors or controllers
- No screen dimensions stored in sensors/controllers

## Version History

- **Current Version**: Full FTMS Bluetooth support with MVC architecture
- **Features**: 
  - **Bluetooth Low Energy (BLE)** - FTMS service for Rouvy, Zwift, etc.
  - **Indoor Bike Simulation** - Receives hill grade from apps
  - **Workout Timer** - Start/pause/reset stopwatch
  - Gear-based load control (7 gears)
  - Incline simulation (-20% to +20%)
  - Real-time speed measurement from hardware sensors
  - Centralized display logic (View class)
  - Centralized input handling (ButtonController class)
  - Pairing mode for easy Bluetooth connection

## Test Scripts

Several test scripts are included for debugging:

| Script | Purpose |
|--------|---------|
| `test_ble.py` | Test FTMS Bluetooth service and connection |
| `test_buttons.py` | Test button inputs and debouncing |
| `test_speed_sensors.py` | Test wheel and crank sensors |
| `test_motor_sensors.py` | Test motor position and calibration |
| `test_calculate_gear_ratio.py` | Verify gear ratio calculations |

Run a test script:
```python
exec(open('test_ble.py').read())
```
