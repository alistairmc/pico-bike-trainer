"""Bluetooth Low Energy (BLE) Controller for Bike Trainer.

This class implements the Fitness Machine Service (FTMS) to broadcast
indoor bike data and allows external programs (like Rouvy, Zwift, etc.)
to control incline/resistance settings.

Implements:
- FTMS (Fitness Machine Service) 0x1826 - Main smart trainer service
- CSC (Cycling Speed and Cadence) 0x1816 - Speed and cadence data

Requires Raspberry Pi Pico W (with Bluetooth support).

CREDITS & LICENSING:
--------------------
This file is part of the Pico Bike Trainer project.
Copyright (C) 2022 Alistair Mcgranaghan
SPDX-License-Identifier: GPL-3.0-or-later

The FTMS implementation in this file is based on and inspired by the
SmartSpin2k project by Anthony Doud & Joel Baranick:
    https://github.com/doudar/SmartSpin2k

SmartSpin2k is licensed under GPL-2.0 (GNU General Public License v2).
The FTMS constants, flag definitions, and control point handling patterns
were adapted from SmartSpin2k's BLE implementation files:
    - BLE_Definitions.h
    - BLE_Fitness_Machine_Service.cpp  
    - Constants.h

Original SmartSpin2k Copyright (C) 2020 Anthony Doud & Joel Baranick
Original SmartSpin2k License: GPL-2.0-only

This adapted code is incorporated into this GPL-3.0 licensed project
per GPL compatibility rules.

The Bluetooth FTMS specification is from the Bluetooth SIG:
    https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/
"""

import ubluetooth
from micropython import const
import struct
import utime


# ============================================================================
# BLE Service UUIDs (Standard Bluetooth SIG)
# ============================================================================

# Fitness Machine Service (FTMS) - Primary service for smart trainers
_FTMS_UUID = ubluetooth.UUID(0x1826)
_FTMS_FEATURE_UUID = ubluetooth.UUID(0x2ACC)           # Feature characteristic
_FTMS_INDOOR_BIKE_DATA_UUID = ubluetooth.UUID(0x2AD2)  # Indoor bike data
_FTMS_CONTROL_POINT_UUID = ubluetooth.UUID(0x2AD9)     # Control point
_FTMS_STATUS_UUID = ubluetooth.UUID(0x2ADA)            # Machine status
_FTMS_TRAINING_STATUS_UUID = ubluetooth.UUID(0x2AD3)   # Training status
_FTMS_RESISTANCE_RANGE_UUID = ubluetooth.UUID(0x2AD6)  # Resistance level range
_FTMS_POWER_RANGE_UUID = ubluetooth.UUID(0x2AD8)       # Power range
_FTMS_INCLINATION_RANGE_UUID = ubluetooth.UUID(0x2AD5) # Inclination range

# Cycling Speed and Cadence Service (CSCS) - For basic speed/cadence
_CSCS_UUID = ubluetooth.UUID(0x1816)
_CSCS_MEASUREMENT_UUID = ubluetooth.UUID(0x2A5B)
_CSCS_FEATURE_UUID = ubluetooth.UUID(0x2A5C)

# ============================================================================
# FTMS Indoor Bike Data Flags (Table 4.9)
# ============================================================================
_IBD_MORE_DATA = const(1 << 0)
_IBD_AVG_SPEED = const(1 << 1)
_IBD_INST_CADENCE = const(1 << 2)
_IBD_AVG_CADENCE = const(1 << 3)
_IBD_TOTAL_DISTANCE = const(1 << 4)
_IBD_RESISTANCE_LEVEL = const(1 << 5)
_IBD_INST_POWER = const(1 << 6)
_IBD_AVG_POWER = const(1 << 7)
_IBD_EXPENDED_ENERGY = const(1 << 8)
_IBD_HEART_RATE = const(1 << 9)
_IBD_METABOLIC_EQ = const(1 << 10)
_IBD_ELAPSED_TIME = const(1 << 11)
_IBD_REMAINING_TIME = const(1 << 12)

# ============================================================================
# FTMS Feature Flags (Table 4.3)
# ============================================================================
_FF_AVG_SPEED = const(1 << 0)
_FF_CADENCE = const(1 << 1)
_FF_TOTAL_DISTANCE = const(1 << 2)
_FF_INCLINATION = const(1 << 3)
_FF_ELEVATION_GAIN = const(1 << 4)
_FF_PACE = const(1 << 5)
_FF_STEP_COUNT = const(1 << 6)
_FF_RESISTANCE_LEVEL = const(1 << 7)
_FF_STRIDE_COUNT = const(1 << 8)
_FF_EXPENDED_ENERGY = const(1 << 9)
_FF_HEART_RATE = const(1 << 10)
_FF_METABOLIC_EQ = const(1 << 11)
_FF_ELAPSED_TIME = const(1 << 12)
_FF_REMAINING_TIME = const(1 << 13)
_FF_POWER_MEASUREMENT = const(1 << 14)
_FF_FORCE_ON_BELT = const(1 << 15)
_FF_USER_DATA_RETENTION = const(1 << 16)

# ============================================================================
# FTMS Target Setting Feature Flags (Table 4.4)
# ============================================================================
_TF_SPEED_TARGET = const(1 << 0)
_TF_INCLINATION_TARGET = const(1 << 1)
_TF_RESISTANCE_TARGET = const(1 << 2)
_TF_POWER_TARGET = const(1 << 3)
_TF_HEART_RATE_TARGET = const(1 << 4)
_TF_EXPENDED_ENERGY_CONFIG = const(1 << 5)
_TF_STEP_NUMBER_CONFIG = const(1 << 6)
_TF_STRIDE_NUMBER_CONFIG = const(1 << 7)
_TF_DISTANCE_CONFIG = const(1 << 8)
_TF_TRAINING_TIME_CONFIG = const(1 << 9)
_TF_TIME_2HR_ZONES = const(1 << 10)
_TF_TIME_3HR_ZONES = const(1 << 11)
_TF_TIME_5HR_ZONES = const(1 << 12)
_TF_INDOOR_BIKE_SIM = const(1 << 13)
_TF_WHEEL_CIRCUMFERENCE = const(1 << 14)
_TF_SPIN_DOWN = const(1 << 15)
_TF_TARGETED_CADENCE = const(1 << 16)

# ============================================================================
# FTMS Control Point Procedures (Table 4.16.1)
# ============================================================================
_CP_REQUEST_CONTROL = const(0x00)
_CP_RESET = const(0x01)
_CP_SET_TARGET_SPEED = const(0x02)
_CP_SET_TARGET_INCLINATION = const(0x03)
_CP_SET_TARGET_RESISTANCE = const(0x04)
_CP_SET_TARGET_POWER = const(0x05)
_CP_SET_TARGET_HEART_RATE = const(0x06)
_CP_START_OR_RESUME = const(0x07)
_CP_STOP_OR_PAUSE = const(0x08)
_CP_SET_INDOOR_BIKE_SIM = const(0x11)
_CP_SET_WHEEL_CIRCUMFERENCE = const(0x12)
_CP_SPIN_DOWN_CONTROL = const(0x13)
_CP_SET_TARGETED_CADENCE = const(0x14)
_CP_RESPONSE_CODE = const(0x80)

# ============================================================================
# FTMS Control Point Result Codes (Table 4.24)
# ============================================================================
_RESULT_SUCCESS = const(0x01)
_RESULT_NOT_SUPPORTED = const(0x02)
_RESULT_INVALID_PARAM = const(0x03)
_RESULT_OPERATION_FAILED = const(0x04)
_RESULT_CONTROL_NOT_PERMITTED = const(0x05)

# ============================================================================
# FTMS Status Codes (Table 4.17)
# ============================================================================
_STATUS_RESET = const(0x01)
_STATUS_STOPPED_PAUSED = const(0x02)
_STATUS_STOPPED_SAFETY = const(0x03)
_STATUS_STARTED_RESUMED = const(0x04)
_STATUS_TARGET_SPEED_CHANGED = const(0x05)
_STATUS_TARGET_INCLINE_CHANGED = const(0x06)
_STATUS_TARGET_RESISTANCE_CHANGED = const(0x07)
_STATUS_TARGET_POWER_CHANGED = const(0x08)
_STATUS_INDOOR_BIKE_SIM_CHANGED = const(0x12)

# ============================================================================
# BLE Advertising
# ============================================================================
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)

# ============================================================================
# BLE IRQ Events
# ============================================================================
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

# ============================================================================
# BLE Characteristic Flags
# ============================================================================
_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)


class BLEController:
    """BLE Controller implementing FTMS for smart bike trainer compatibility.

    Implements:
    - Fitness Machine Service (FTMS) for Rouvy, Zwift, etc.
    - Cycling Speed and Cadence Service (CSCS) for basic apps
    """

    def __init__(self, name="Pico Bike", speed_controller=None, load_controller=None):
        """Initialize BLE controller.

        Args:
            name: BLE device name (max 16 chars for FTMS advertising).
            speed_controller: SpeedController instance for speed/RPM data.
            load_controller: LoadController instance for resistance control.
        """
        self.name = name[:16]  # Limit name for advertising space
        self.speed_controller = speed_controller
        self.load_controller = load_controller

        # BLE state
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        print(f"BLE: Activated (active={self.ble.active()})")

        self.connected = False
        self.conn_handle = None
        self.control_granted = False

        # Cumulative counters for CSC
        self.wheel_revolutions = 0
        self.crank_revolutions = 0
        self.last_wheel_event_time = 0
        self.last_crank_event_time = 0
        self.last_wheel_rpm = 0
        self.last_crank_rpm = 0
        self.last_update_time = 0

        # Target values from control point
        self.target_incline = 0.0      # -20.0 to +20.0 %
        self.target_resistance = 0     # 0.1 to 100 (0.1% units)
        self.target_power = 0          # Watts
        self.sim_wind_speed = 0        # m/s * 1000
        self.sim_grade = 0             # % * 100
        self.sim_crr = 0               # Coefficient * 10000
        self.sim_cw = 0                # kg/m * 100

        # Pairing mode
        self.pairing_mode = False
        self.pairing_mode_start_time = 0
        self.pairing_mode_duration_ms = 120000
        self.normal_name = self.name
        self.pairing_name = self.name[:11] + " PAIR"

        # Register IRQ handler
        self.ble.irq(self._irq_handler)

        # Register services
        self._register_services()

        # Start advertising
        self._advertise()

        print(f"BLE: Initialized as '{self.name}'")

    def _irq_handler(self, event, data):
        """Handle BLE IRQ events."""
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, addr_type, addr = data
            self.connected = True
            self.conn_handle = conn_handle
            print(f"BLE: Connected (handle={conn_handle})")
            if self.pairing_mode:
                self.stop_pairing_mode()

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            self.connected = False
            self.conn_handle = None
            self.control_granted = False
            print("BLE: Disconnected")
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            value = self.ble.gatts_read(value_handle)
            if value_handle == self.ftms_control_point_handle:
                self._handle_control_point(value)

    def _register_services(self):
        """Register FTMS and CSCS services."""
        
        # FTMS characteristics
        ftms_feature = (_FTMS_FEATURE_UUID, _FLAG_READ)
        ftms_indoor_bike_data = (_FTMS_INDOOR_BIKE_DATA_UUID, _FLAG_NOTIFY)
        ftms_control_point = (_FTMS_CONTROL_POINT_UUID, _FLAG_WRITE | _FLAG_INDICATE)
        ftms_status = (_FTMS_STATUS_UUID, _FLAG_NOTIFY)
        ftms_training_status = (_FTMS_TRAINING_STATUS_UUID, _FLAG_READ | _FLAG_NOTIFY)
        ftms_resistance_range = (_FTMS_RESISTANCE_RANGE_UUID, _FLAG_READ)
        ftms_inclination_range = (_FTMS_INCLINATION_RANGE_UUID, _FLAG_READ)

        # CSCS characteristics
        cscs_measurement = (_CSCS_MEASUREMENT_UUID, _FLAG_NOTIFY)
        cscs_feature = (_CSCS_FEATURE_UUID, _FLAG_READ)

        # Register services
        services = self.ble.gatts_register_services((
            (_FTMS_UUID, (
                ftms_feature,
                ftms_indoor_bike_data,
                ftms_control_point,
                ftms_status,
                ftms_training_status,
                ftms_resistance_range,
                ftms_inclination_range,
            )),
            (_CSCS_UUID, (
                cscs_measurement,
                cscs_feature,
            )),
        ))

        # Unpack handles
        ftms_handles = services[0]
        cscs_handles = services[1]

        self.ftms_feature_handle = ftms_handles[0]
        self.ftms_indoor_bike_data_handle = ftms_handles[1]
        self.ftms_control_point_handle = ftms_handles[2]
        self.ftms_status_handle = ftms_handles[3]
        self.ftms_training_status_handle = ftms_handles[4]
        self.ftms_resistance_range_handle = ftms_handles[5]
        self.ftms_inclination_range_handle = ftms_handles[6]

        self.cscs_measurement_handle = cscs_handles[0]
        self.cscs_feature_handle = cscs_handles[1]

        # Set initial values
        self._set_feature_values()
        self._set_range_values()
        
        print("BLE: Services registered (FTMS + CSCS)")

    def _set_feature_values(self):
        """Set FTMS and CSCS feature characteristic values."""
        # FTMS Feature: 8 bytes (4 bytes machine features + 4 bytes target features)
        machine_features = (
            _FF_CADENCE |
            _FF_INCLINATION |
            _FF_RESISTANCE_LEVEL |
            _FF_POWER_MEASUREMENT
        )
        target_features = (
            _TF_INCLINATION_TARGET |
            _TF_RESISTANCE_TARGET |
            _TF_INDOOR_BIKE_SIM
        )
        ftms_feature_data = struct.pack("<II", machine_features, target_features)
        self.ble.gatts_write(self.ftms_feature_handle, ftms_feature_data)

        # CSCS Feature: Wheel and Crank supported
        cscs_feature_data = struct.pack("<H", 0x0003)
        self.ble.gatts_write(self.cscs_feature_handle, cscs_feature_data)

        # Training status: Idle
        training_status = struct.pack("<BB", 0x00, 0x01)  # flags=0, status=Idle
        self.ble.gatts_write(self.ftms_training_status_handle, training_status)

    def _set_range_values(self):
        """Set FTMS range characteristic values."""
        # Resistance Level Range: min, max, increment (sint16 * 0.1)
        # Range: 1 to 100 (0.1% to 10.0%)
        resistance_range = struct.pack("<hhh", 10, 1000, 10)  # 1.0 to 100.0, step 1.0
        self.ble.gatts_write(self.ftms_resistance_range_handle, resistance_range)

        # Inclination Range: min, max, increment (sint16 * 0.1%)
        # Range: -20.0% to +20.0%
        inclination_range = struct.pack("<hhh", -200, 200, 1)  # -20.0 to +20.0, step 0.1
        self.ble.gatts_write(self.ftms_inclination_range_handle, inclination_range)

    def _advertise(self):
        """Start BLE advertising."""
        try:
            self.ble.gap_advertise(None)
        except:
            pass

        display_name = self.pairing_name if self.pairing_mode else self.normal_name
        name_bytes = bytes(display_name[:16], "utf-8")

        adv_data = bytearray()
        # Flags
        adv_data.extend(struct.pack("BBB", 2, _ADV_TYPE_FLAGS, 0x06))
        # Name
        adv_data.extend(struct.pack("BB", len(name_bytes) + 1, _ADV_TYPE_NAME))
        adv_data.extend(name_bytes)
        # FTMS UUID (16-bit)
        if len(adv_data) + 4 <= 31:
            adv_data.extend(struct.pack("BB", 3, _ADV_TYPE_UUID16_COMPLETE))
            adv_data.extend(struct.pack("<H", 0x1826))

        adv_interval = 100000 if self.pairing_mode else 200000
        self.ble.gap_advertise(adv_interval, adv_data=adv_data)
        print(f"BLE: Advertising as '{display_name}' (FTMS)")

    def _handle_control_point(self, value):
        """Handle FTMS Control Point writes."""
        if len(value) < 1:
            return

        op_code = value[0]
        result = _RESULT_SUCCESS
        response_params = bytes()

        print(f"BLE: Control Point Op={op_code:#x} Data={value.hex()}")

        if op_code == _CP_REQUEST_CONTROL:
            self.control_granted = True
            print("BLE: Control granted")

        elif op_code == _CP_RESET:
            self.target_incline = 0.0
            self.target_resistance = 0
            self.target_power = 0
            self._notify_status(_STATUS_RESET)
            print("BLE: Reset")

        elif op_code == _CP_SET_TARGET_INCLINATION:
            if len(value) >= 3:
                # Inclination in 0.1% units (sint16)
                incline_raw = struct.unpack("<h", value[1:3])[0]
                self.target_incline = incline_raw / 10.0
                if self.load_controller:
                    self.load_controller.set_incline(self.target_incline)
                self._notify_status(_STATUS_TARGET_INCLINE_CHANGED, value[1:3])
                print(f"BLE: Target incline = {self.target_incline:.1f}%")
            else:
                result = _RESULT_INVALID_PARAM

        elif op_code == _CP_SET_TARGET_RESISTANCE:
            if len(value) >= 3:
                # Resistance in 0.1 units (sint16)
                self.target_resistance = struct.unpack("<h", value[1:3])[0]
                resistance_pct = self.target_resistance / 10.0
                if self.load_controller:
                    # Convert resistance (0-100) to incline for our system
                    self.load_controller.set_incline(resistance_pct)
                self._notify_status(_STATUS_TARGET_RESISTANCE_CHANGED, value[1:3])
                print(f"BLE: Target resistance = {resistance_pct:.1f}")
            else:
                result = _RESULT_INVALID_PARAM

        elif op_code == _CP_SET_TARGET_POWER:
            if len(value) >= 3:
                self.target_power = struct.unpack("<H", value[1:3])[0]
                self._notify_status(_STATUS_TARGET_POWER_CHANGED, value[1:3])
                print(f"BLE: Target power = {self.target_power}W")
            else:
                result = _RESULT_INVALID_PARAM

        elif op_code == _CP_START_OR_RESUME:
            self._notify_status(_STATUS_STARTED_RESUMED)
            self._notify_training_status(0x04)  # Running
            print("BLE: Started/Resumed")

        elif op_code == _CP_STOP_OR_PAUSE:
            param = value[1] if len(value) > 1 else 0x01
            self._notify_status(_STATUS_STOPPED_PAUSED, bytes([param]))
            self._notify_training_status(0x01)  # Idle
            print("BLE: Stopped/Paused")

        elif op_code == _CP_SET_INDOOR_BIKE_SIM:
            if len(value) >= 7:
                # Wind speed (sint16, m/s * 1000)
                self.sim_wind_speed = struct.unpack("<h", value[1:3])[0]
                # Grade (sint16, % * 100)
                self.sim_grade = struct.unpack("<h", value[3:5])[0]
                # CRR (uint8, * 10000)
                self.sim_crr = value[5]
                # CW (uint8, kg/m * 100)
                self.sim_cw = value[6]
                
                # Apply grade as incline
                grade_pct = self.sim_grade / 100.0
                self.target_incline = grade_pct
                if self.load_controller:
                    self.load_controller.set_incline(grade_pct)
                
                self._notify_status(_STATUS_INDOOR_BIKE_SIM_CHANGED, value[1:7])
                print(f"BLE: Sim params - grade={grade_pct:.2f}%")
            else:
                result = _RESULT_INVALID_PARAM

        else:
            result = _RESULT_NOT_SUPPORTED
            print(f"BLE: Unsupported op code {op_code:#x}")

        # Send response
        response = struct.pack("<BBB", _CP_RESPONSE_CODE, op_code, result)
        response += response_params
        self.ble.gatts_write(self.ftms_control_point_handle, response)
        if self.connected:
            self.ble.gatts_indicate(self.conn_handle, self.ftms_control_point_handle)

    def _notify_status(self, status_code, params=bytes()):
        """Notify FTMS status change."""
        if not self.connected:
            return
        status_data = bytes([status_code]) + params
        self.ble.gatts_write(self.ftms_status_handle, status_data)
        self.ble.gatts_notify(self.conn_handle, self.ftms_status_handle, status_data)

    def _notify_training_status(self, status):
        """Notify training status change."""
        if not self.connected:
            return
        data = struct.pack("<BB", 0x00, status)
        self.ble.gatts_write(self.ftms_training_status_handle, data)
        self.ble.gatts_notify(self.conn_handle, self.ftms_training_status_handle, data)

    def update_indoor_bike_data(self):
        """Broadcast FTMS Indoor Bike Data."""
        if not self.connected:
            return

        try:
            # Get current values
            speed_kmh = 0.0
            cadence_rpm = 0.0
            resistance_pct = 0.0
            power_watts = 0

            if self.speed_controller:
                speed_kmh = self.speed_controller.get_calculated_speed() or 0.0
                cadence_rpm = self.speed_controller.get_crank_rpm() or 0.0

            if self.load_controller:
                resistance_pct = self.load_controller.get_current_load_percent() or 0.0

            # Convert speed to FTMS units (km/h * 100)
            speed_ftms = int(speed_kmh * 100)
            
            # Convert cadence to FTMS units (0.5 RPM resolution)
            cadence_ftms = int(cadence_rpm * 2)
            
            # Resistance (0.1 units)
            resistance_ftms = int(resistance_pct * 10)

            # Build Indoor Bike Data
            # Flags: Cadence present, Resistance present, Power present
            flags = _IBD_INST_CADENCE | _IBD_RESISTANCE_LEVEL | _IBD_INST_POWER

            data = struct.pack("<H", flags)          # Flags (2 bytes)
            data += struct.pack("<H", speed_ftms)    # Speed (2 bytes) - always present
            data += struct.pack("<H", cadence_ftms)  # Cadence (2 bytes)
            data += struct.pack("<h", resistance_ftms)  # Resistance (2 bytes, signed)
            data += struct.pack("<h", power_watts)   # Power (2 bytes, signed)

            self.ble.gatts_write(self.ftms_indoor_bike_data_handle, data)
            self.ble.gatts_notify(self.conn_handle, self.ftms_indoor_bike_data_handle, data)

        except Exception as e:
            print(f"BLE: Error in indoor bike data: {e}")

    def update_csc_data(self):
        """Broadcast CSC (speed/cadence) data."""
        if not self.connected:
            return

        try:
            current_time = utime.ticks_ms()
            current_time_1024 = current_time * 1024 // 1000

            wheel_rpm = 0.0
            crank_rpm = 0.0

            if self.speed_controller:
                wheel_rpm = self.speed_controller.get_wheel_rpm() or 0.0
                crank_rpm = self.speed_controller.get_crank_rpm() or 0.0

            # Update cumulative counters
            if self.last_update_time > 0:
                dt_sec = utime.ticks_diff(current_time, self.last_update_time) / 1000.0
                if wheel_rpm > 0:
                    self.wheel_revolutions += int((wheel_rpm / 60.0) * dt_sec)
                    self.last_wheel_event_time = current_time_1024 & 0xFFFF
                if crank_rpm > 0:
                    self.crank_revolutions += int((crank_rpm / 60.0) * dt_sec)
                    self.last_crank_event_time = current_time_1024 & 0xFFFF

            self.last_update_time = current_time

            # Build CSC data (wheel + crank)
            flags = 0x03  # Both wheel and crank present
            data = struct.pack("<B", flags)
            data += struct.pack("<I", self.wheel_revolutions & 0xFFFFFFFF)
            data += struct.pack("<H", self.last_wheel_event_time)
            data += struct.pack("<H", self.crank_revolutions & 0xFFFF)
            data += struct.pack("<H", self.last_crank_event_time)

            self.ble.gatts_write(self.cscs_measurement_handle, data)
            self.ble.gatts_notify(self.conn_handle, self.cscs_measurement_handle, data)

        except Exception as e:
            print(f"BLE: Error in CSC data: {e}")

    def update(self):
        """Update all BLE data broadcasts. Call this regularly."""
        self.update_indoor_bike_data()
        self.update_csc_data()

    # Compatibility methods
    def update_combined_data(self):
        """Alias for update() - maintains compatibility."""
        self.update()

    def update_incline_value(self):
        """Update incline (included in indoor bike data)."""
        pass  # Handled in update_indoor_bike_data

    def update_load_value(self):
        """Update load (included in indoor bike data)."""
        pass  # Handled in update_indoor_bike_data

    def is_connected(self):
        """Check if BLE is connected."""
        return self.connected

    def get_target_incline(self):
        """Get target incline from app."""
        return self.target_incline

    def set_wheel_circumference(self, circumference_mm):
        """Set wheel circumference (for reference)."""
        self.wheel_circumference_mm = circumference_mm

    # Pairing mode methods
    def start_pairing_mode(self):
        """Start pairing mode."""
        if self.pairing_mode:
            return
        self.pairing_mode = True
        self.pairing_mode_start_time = utime.ticks_ms()
        self._advertise()
        print("BLE: Pairing mode started")

    def stop_pairing_mode(self):
        """Stop pairing mode."""
        if not self.pairing_mode:
            return
        self.pairing_mode = False
        self._advertise()
        print("BLE: Pairing mode stopped")

    def update_pairing_mode(self, current_time):
        """Check pairing mode timeout."""
        if not self.pairing_mode:
            return
        elapsed = utime.ticks_diff(current_time, self.pairing_mode_start_time)
        if elapsed >= self.pairing_mode_duration_ms:
            self.stop_pairing_mode()

    def is_pairing_mode(self):
        """Check if in pairing mode."""
        return self.pairing_mode

    def get_pairing_mode_start_time(self):
        """Get pairing mode start time."""
        return self.pairing_mode_start_time if self.pairing_mode else 0

    def get_pairing_mode_duration_ms(self):
        """Get pairing mode duration."""
        return self.pairing_mode_duration_ms

    def get_status(self):
        """Get BLE status."""
        return {
            'active': self.ble.active(),
            'connected': self.connected,
            'pairing_mode': self.pairing_mode,
            'device_name': self.name,
            'control_granted': self.control_granted
        }

    def print_status(self):
        """Print BLE status."""
        status = self.get_status()
        print("BLE Status:", status)
