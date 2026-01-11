# Pico Bike Trainer

A Raspberry Pi Pico-based bike trainer system that provides realistic resistance simulation based on gear selection and incline settings. The system uses hall sensors to measure speed and motor position, and controls resistance through an L298N motor controller.

## Table of Contents

- [Overview](#overview)
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
| **2** | Decrement Gear | INPUT | Decrement gear (PULL_UP) |
| **3** | Increment Gear | INPUT | Increment gear (PULL_UP) |
| **14** | Increase Incline | INPUT | Increase incline/uphill (PULL_UP) |
| **16** | Toggle Unit | INPUT | Toggle speed unit (kmph/mph) (PULL_UP) |
| **18** | Decrease Incline | INPUT | Decrease incline/downhill (PULL_UP) |
| **20** | Control Button | INPUT | Control button (PULL_UP, currently unused) |

### GPIO Summary
- **Total GPIO Pins Used**: 18
- **Input Pins**: 10 (all with PULL_UP)
  - Motor sensors: 0, 1
  - Speed sensors: 4, 7
  - Buttons: 2, 3, 14, 16, 18, 20
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
- **Purpose**: Manages all speed calculations and unit conversions
- **GPIO**: None (software controller)
- **Features**:
  - Converts RPM to speed (km/h or mph)
  - Manages unit conversion (kmph ↔ mph)
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
- **GPIO**: Pins 2, 3, 14, 16, 18, 20 (button inputs)
- **Features**:
  - Handles all button reading and debouncing
  - Dispatches actions to appropriate controllers
  - Separates input handling from business logic (MVC pattern)
  - Button functions:
    - GPIO 2: Increment gear
    - GPIO 3: Decrement gear
    - GPIO 14: Increase incline (uphill)
    - GPIO 16: Toggle speed unit (kmph/mph)
    - GPIO 18: Decrease incline (downhill)
    - GPIO 20: Control button (currently unused)

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
- **SpeedController**: Converts RPM to speed (km/h or mph)
  - Calculates speed from wheel RPM multiplied by virtual gear ratio
  - Handles unit conversion (kmph ↔ mph)
  - Manages calibration and wheel circumference
- **Calculated Speed**: Wheel RPM × Gear Ratio, converted to km/h or mph
- Wheel RPM (WRPM) displayed
- Configurable wheel circumference

### Display
- **View Class**: Centralized display rendering (Model-View-Controller pattern)
- Real-time calculated speed display (wheel RPM × gear ratio)
- Current gear display
- Wheel RPM (WRPM) display
- Load percentage display
- Incline percentage display
- 4 Hz update rate (250ms intervals)
- All display logic separated from business logic

### User Controls
- **Gear Selection**: Increment/Decrement gear buttons (GPIO 2/3)
- **Incline Control**: Increase/Decrease incline buttons (GPIO 14/18, ±5% per press)
- **Speed Unit Toggle**: Toggle unit button (GPIO 16, kmph ↔ mph)

## Hardware Requirements

### Required Components
1. **Raspberry Pi Pico** (or Pico W)
2. **LCD Display**: 1.3" 240x240 SPI LCD
3. **L298N Motor Driver**: For controlling resistance motor
4. **Hall Sensors**: 
   - Motor rotation sensor (GPIO 0)
   - Motor stop trigger (GPIO 1)
   - Crank sensor (GPIO 7)
   - Wheel speed sensor (GPIO 4)
5. **Buttons/Joystick**: For user input
6. **Resistance Motor**: Controlled by L298N

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
   - Connect buttons to GPIO pins 2, 3, 14, 16, 18, 20

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
- **Gear Changes**: Use Left/Right buttons
- **Incline Adjustment**: Use Up/Down buttons
- **Load**: Automatically adjusted based on gear and incline

### Display Information
- **Speed**: Calculated speed (wheel RPM × gear ratio) in km/h or mph
- **WRPM**: Wheel RPM (flywheel/wheel speed)
- **Gear**: Current gear (1-7)
- **Load**: Current load percentage (0-100%)
- **Incline**: Current incline percentage (-100% to +100%)

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

## License

This project is provided as-is for educational and personal use.

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

- **Current Version**: MVC architecture with View and ButtonController classes
- **Features**: 
  - Gear-based load control
  - Incline simulation (-100% to +100%)
  - Real-time speed measurement from hardware sensors only
  - Centralized display logic (View class)
  - Centralized input handling (ButtonController class)
  - No simulation or testing modes - hardware sensors required
