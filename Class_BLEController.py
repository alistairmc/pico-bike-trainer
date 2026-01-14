"""Bluetooth Low Energy (BLE) Controller for Bike Trainer.

This class implements BLE services to broadcast wheel speed and crank RPM,
and allows external programs (like Rovy) to control incline settings.

Requires Raspberry Pi Pico W (with Bluetooth support).
"""

import ubluetooth
from micropython import const
import struct
import utime


# BLE UUIDs - Cycling Speed and Cadence Service (CSCS)
_CSCS_UUID = ubluetooth.UUID(0x1816)  # Cycling Speed and Cadence Service
_CSCS_CHAR_SPEED_UUID = ubluetooth.UUID(0x2A5B)  # CSC Measurement
_CSCS_CHAR_CADENCE_UUID = ubluetooth.UUID(0x2A5F)  # CSC Feature

# Custom service for incline control
_INCLINE_SERVICE_UUID = ubluetooth.UUID("12345678-1234-1234-1234-123456789abc")
_INCLINE_CHAR_UUID = ubluetooth.UUID("12345678-1234-1234-1234-123456789abd")

# BLE advertising
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID128_MORE = const(0x6)

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICES = const(9)
_IRQ_GATTC_SERVICE_RESULT = const(10)
_IRQ_GATTC_CHARACTERISTICS = const(11)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(12)
_IRQ_GATTC_DESCRIPTORS = const(13)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_WRITE_STATUS = const(16)
_IRQ_GATTC_NOTIFY = const(17)
_IRQ_GATTC_INDICATE = const(18)
_IRQ_GATTS_INDICATE_DONE = const(19)
_IRQ_GET_SECRET = const(29)
_IRQ_SET_SECRET = const(30)

_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)


class BLEController:
    """BLE Controller for broadcasting bike trainer data and receiving incline commands.

    Implements:
    - Cycling Speed and Cadence Service (CSCS) for wheel speed and crank RPM
    - Custom service for incline control
    """

    def __init__(self, name="Pico Bike Trainer", speed_controller=None, load_controller=None):
        """Initialize BLE controller.

        Args:
            name: BLE device name (default: "Pico Bike Trainer").
            speed_controller: SpeedController instance for speed/RPM data (default: None).
            load_controller: LoadController instance for incline control (default: None).
        """
        self.name = name
        self.speed_controller = speed_controller
        self.load_controller = load_controller

        # BLE state
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.connected = False
        self.conn_handle = None

        # Wheel revolution data (for cumulative wheel revolutions)
        self.wheel_revolutions = 0
        self.last_wheel_event_time = 0  # 1/1024 second units
        self.wheel_circumference_mm = 2075  # 26-inch wheel in mm (default)
        self.last_wheel_rpm = 0
        self.wheel_rev_counter = 0  # Track actual wheel revolutions from sensor

        # Crank revolution data
        self.crank_revolutions = 0
        self.last_crank_event_time = 0  # 1/1024 second units
        self.last_crank_rpm = 0
        self.crank_rev_counter = 0  # Track actual crank revolutions from sensor

        # Incline control
        self.target_incline = 0.0  # Target incline from BLE

        # Pairing mode
        self.pairing_mode = False
        self.pairing_mode_start_time = 0
        self.pairing_mode_duration_ms = 120000  # 120 seconds
        self.normal_name = name
        self.pairing_name = name + " [PAIRING]"

        # Register BLE IRQ handler
        self.ble.irq(self._irq_handler)

        # Register services
        self._register_services()

        # Start advertising
        self._advertise()

        print(f"BLE initialized: {self.name}")

    def _irq_handler(self, event, data):
        """Handle BLE IRQ events."""
        if event == _IRQ_CENTRAL_CONNECT:
            # A central has connected to this peripheral
            conn_handle, addr_type, addr = data
            self.connected = True
            self.conn_handle = conn_handle
            print(f"BLE: Connected to {bytes(addr).hex()}")

            # Exit pairing mode when connected
            if self.pairing_mode:
                self.stop_pairing_mode()
                print("BLE: Pairing mode ended - device connected")

        elif event == _IRQ_CENTRAL_DISCONNECT:
            # A central has disconnected from this peripheral
            conn_handle, addr_type, addr = data
            self.connected = False
            self.conn_handle = None
            print("BLE: Disconnected")
            # Restart advertising
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            # A client has written to a characteristic
            conn_handle, value_handle = data
            value = self.ble.gatts_read(value_handle)

            # Check if it's the incline control characteristic
            if value_handle == self.incline_char_handle:
                self._handle_incline_write(value)

    def _register_services(self):
        """Register BLE services and characteristics."""
        # Cycling Speed and Cadence Service (CSCS)
        # Characteristic: CSC Measurement (speed)
        speed_char = (
            _CSCS_CHAR_SPEED_UUID,
            _FLAG_READ | _FLAG_NOTIFY,
        )

        # Characteristic: CSC Feature
        feature_char = (
            _CSCS_CHAR_CADENCE_UUID,
            _FLAG_READ,
        )

        # Custom Incline Control Service
        incline_char = (
            _INCLINE_CHAR_UUID,
            _FLAG_READ | _FLAG_WRITE | _FLAG_NOTIFY,
        )

        # Register services
        # gatts_register_services expects: ((service1_uuid, (char1, char2, ...)), (service2_uuid, (char1, ...)), ...)
        # Returns: ((char1_handle, char2_handle, ...), (char1_handle, ...), ...)
        # One tuple per service, each containing handles for all characteristics in that service
        services = self.ble.gatts_register_services((
            (_CSCS_UUID, (speed_char, feature_char)),
            (_INCLINE_SERVICE_UUID, (incline_char,)),
        ))

        # Unpack service handles
        # services is a tuple: (cscs_service_tuple, incline_service_tuple)
        # Each service tuple contains handles for all characteristics in that service
        try:
            # First service (CSCS) has 2 characteristics
            if len(services) >= 1 and len(services[0]) >= 2:
                self.speed_char_handle = services[0][0]
                self.feature_char_handle = services[0][1]
            else:
                raise ValueError(f"Unexpected service structure: {services}")

            # Second service (Incline) has 1 characteristic
            if len(services) >= 2 and len(services[1]) >= 1:
                self.incline_char_handle = services[1][0]
            else:
                raise ValueError(f"Unexpected service structure: {services}")
        except (IndexError, ValueError) as e:
            print(f"Error unpacking services: {e}")
            print(f"Services structure: {services}")
            print(f"Services length: {len(services)}")
            if len(services) > 0:
                print(f"First service length: {len(services[0])}")
            if len(services) > 1:
                print(f"Second service length: {len(services[1])}")
            raise

        # Set initial values
        # CSC Feature: Wheel and Crank supported
        self.ble.gatts_write(self.feature_char_handle, struct.pack("<H", 0x0003))

        # Initial incline value
        self.ble.gatts_write(self.incline_char_handle, struct.pack("<f", 0.0))

    def _advertise(self):
        """Start BLE advertising."""
        # Use pairing name if in pairing mode, otherwise normal name
        display_name = self.pairing_name if self.pairing_mode else self.normal_name
        name = bytes(display_name, "utf-8")
        adv_data = bytearray()
        adv_data.extend(struct.pack("BB", _ADV_TYPE_FLAGS, 0x06))
        adv_data.extend(struct.pack("BB", len(name) + 1, _ADV_TYPE_NAME))
        adv_data.extend(name)

        # Add CSCS UUID
        adv_data.extend(struct.pack("BB", 3, _ADV_TYPE_UUID16_COMPLETE))
        adv_data.extend(struct.pack("<H", 0x1816))  # CSCS UUID

        # In pairing mode, advertise more frequently for better discoverability
        adv_interval = 200000 if self.pairing_mode else 500000  # Faster in pairing mode
        self.ble.gap_advertise(adv_interval, adv_data=adv_data)
        print(f"BLE: Advertising as '{display_name}'")

    def _handle_incline_write(self, value):
        """Handle incline control write from external device.

        Args:
            value: Byte array containing incline value (float).
        """
        try:
            if len(value) == 4:  # Float is 4 bytes
                incline = struct.unpack("<f", value)[0]
                # Clamp to valid range
                incline = max(-100.0, min(100.0, incline))
                self.target_incline = incline

                # Apply to load controller
                if self.load_controller is not None:
                    self.load_controller.set_incline(incline)

                print(f"BLE: Incline set to {incline:.1f}%")
        except Exception as e:
            print(f"BLE: Error handling incline write: {e}")

    def update_speed_data(self):
        """Update and broadcast wheel speed data.

        Should be called regularly (e.g., every second or when speed changes).
        """
        if not self.connected or self.speed_controller is None:
            return

        try:
            wheel_rpm = self.speed_controller.get_wheel_rpm()

            if wheel_rpm > 0:
                # Calculate wheel revolutions (cumulative)
                current_time_1024 = utime.ticks_ms() * 1024 // 1000

                # Increment wheel revolutions based on RPM
                # This is a simplified approach - in real implementation,
                # you'd track actual wheel revolutions from sensor
                if self.last_wheel_event_time > 0:
                    time_diff = current_time_1024 - self.last_wheel_event_time
                    # Approximate: if we've been at this RPM for time_diff, how many revs?
                    # For simplicity, we'll just increment based on time
                    pass  # Would need actual wheel sensor pulse counting

                # Update event time
                self.last_wheel_event_time = current_time_1024

                # Build CSC Measurement data
                # Flags: Wheel revolution data present (bit 0)
                flags = 0x01

                # Cumulative wheel revolutions (32-bit)
                # For now, we'll use a calculated value based on RPM
                # In production, track actual wheel revolutions from sensor
                wheel_revs = self.wheel_revolutions

                # Last wheel event time (16-bit, 1/1024 second units)
                event_time = current_time_1024 & 0xFFFF

                # Pack data: flags (1 byte) + wheel_revs (4 bytes) + event_time (2 bytes)
                csc_data = struct.pack("<B", flags)
                csc_data += struct.pack("<I", wheel_revs)
                csc_data += struct.pack("<H", event_time)

                # Notify connected devices
                self.ble.gatts_notify(self.conn_handle, self.speed_char_handle, csc_data)

        except Exception as e:
            print(f"BLE: Error updating speed data: {e}")

    def update_cadence_data(self):
        """Update and broadcast crank cadence (RPM) data.

        Should be called regularly when cadence changes.
        """
        if not self.connected or self.speed_controller is None:
            return

        try:
            crank_rpm = self.speed_controller.get_crank_rpm()

            if crank_rpm > 0:
                # Calculate crank revolutions (cumulative)
                current_time_1024 = utime.ticks_ms() * 1024 // 1000

                # Increment crank revolutions
                # Similar to wheel - would need actual sensor pulse counting
                if self.last_crank_event_time > 0:
                    time_diff = current_time_1024 - self.last_crank_event_time
                    # Would calculate based on actual crank sensor pulses

                self.last_crank_event_time = current_time_1024

                # Build CSC Measurement data with cadence
                # Flags: Crank revolution data present (bit 1)
                flags = 0x02

                # Cumulative crank revolutions (16-bit)
                crank_revs = self.crank_revolutions & 0xFFFF

                # Last crank event time (16-bit, 1/1024 second units)
                event_time = current_time_1024 & 0xFFFF

                # Pack data: flags (1 byte) + crank_revs (2 bytes) + event_time (2 bytes)
                csc_data = struct.pack("<B", flags)
                csc_data += struct.pack("<H", crank_revs)
                csc_data += struct.pack("<H", event_time)

                # Notify connected devices
                self.ble.gatts_notify(self.conn_handle, self.speed_char_handle, csc_data)

        except Exception as e:
            print(f"BLE: Error updating cadence data: {e}")

    def update_combined_data(self):
        """Update and broadcast combined wheel speed and cadence data.

        This is the recommended approach - send both together.
        Should be called regularly (e.g., every second or when data changes).
        """
        if not self.connected or self.speed_controller is None:
            return

        try:
            wheel_rpm = self.speed_controller.get_wheel_rpm()
            crank_rpm = self.speed_controller.get_crank_rpm()

            current_time_ms = utime.ticks_ms()
            current_time_1024 = current_time_ms * 1024 // 1000

            # Update wheel revolutions based on RPM change
            # This is a simplified approach - ideally track actual sensor pulses
            if wheel_rpm > 0:
                # Estimate revolutions based on RPM and time
                if self.last_wheel_rpm > 0:
                    # Calculate time since last update (approximate)
                    time_diff_sec = 1.0  # Assume 1 second between updates
                    revs_in_period = (wheel_rpm / 60.0) * time_diff_sec
                    self.wheel_revolutions += int(revs_in_period)
                    self.wheel_rev_counter += int(revs_in_period)

                self.last_wheel_event_time = current_time_1024 & 0xFFFF
                self.last_wheel_rpm = wheel_rpm

            # Update crank revolutions based on RPM change
            if crank_rpm > 0:
                if self.last_crank_rpm > 0:
                    time_diff_sec = 1.0  # Assume 1 second between updates
                    revs_in_period = (crank_rpm / 60.0) * time_diff_sec
                    self.crank_revolutions += int(revs_in_period)
                    self.crank_rev_counter += int(revs_in_period)

                self.last_crank_event_time = current_time_1024 & 0xFFFF
                self.last_crank_rpm = crank_rpm

            # Build CSC Measurement data with both wheel and crank
            # Flags: Both wheel (bit 0) and crank (bit 1) data present
            flags = 0x03

            # Cumulative wheel revolutions (32-bit)
            wheel_revs = self.wheel_revolutions & 0xFFFFFFFF

            # Last wheel event time (16-bit, wraps every ~64 seconds)
            wheel_event_time = self.last_wheel_event_time

            # Cumulative crank revolutions (16-bit, wraps at 65536)
            crank_revs = self.crank_revolutions & 0xFFFF

            # Last crank event time (16-bit)
            crank_event_time = self.last_crank_event_time

            # Pack data: flags (1 byte) + wheel_revs (4 bytes) + wheel_time (2 bytes) +
            #            crank_revs (2 bytes) + crank_time (2 bytes) = 11 bytes total
            csc_data = struct.pack("<B", flags)
            csc_data += struct.pack("<I", wheel_revs)
            csc_data += struct.pack("<H", wheel_event_time)
            csc_data += struct.pack("<H", crank_revs)
            csc_data += struct.pack("<H", crank_event_time)

            # Notify connected devices
            self.ble.gatts_notify(self.conn_handle, self.speed_char_handle, csc_data)

        except Exception as e:
            print(f"BLE: Error updating combined data: {e}")

    def update_incline_value(self):
        """Update incline characteristic value (for reading by connected devices)."""
        if not self.connected or self.load_controller is None:
            return

        try:
            current_incline = self.load_controller.get_incline()
            incline_data = struct.pack("<f", current_incline)
            self.ble.gatts_write(self.incline_char_handle, incline_data)
        except Exception as e:
            print(f"BLE: Error updating incline value: {e}")

    def get_target_incline(self):
        """Get target incline value from BLE (set by external device).

        Returns:
            Target incline percentage (-100.0 to 100.0).
        """
        return self.target_incline

    def is_connected(self):
        """Check if BLE is connected.

        Returns:
            True if connected, False otherwise.
        """
        return self.connected

    def set_wheel_circumference(self, circumference_mm):
        """Set wheel circumference for speed calculations.

        Args:
            circumference_mm: Wheel circumference in millimeters.
        """
        self.wheel_circumference_mm = circumference_mm

    def start_pairing_mode(self):
        """Start pairing mode for 120 seconds or until connection is established."""
        if self.pairing_mode:
            return  # Already in pairing mode

        self.pairing_mode = True
        self.pairing_mode_start_time = utime.ticks_ms()
        print("BLE: Pairing mode started (120 seconds or until connected)")

        # Restart advertising with pairing name
        self._advertise()

    def stop_pairing_mode(self):
        """Stop pairing mode and return to normal advertising."""
        if not self.pairing_mode:
            return  # Not in pairing mode

        self.pairing_mode = False
        self.pairing_mode_start_time = 0
        print("BLE: Pairing mode ended")

        # Restart advertising with normal name
        self._advertise()

    def update_pairing_mode(self, current_time):
        """Update pairing mode state - check for timeout.

        Should be called regularly in main loop.

        Args:
            current_time: Current time in milliseconds.
        """
        if not self.pairing_mode:
            return

        # Check if pairing mode has timed out (120 seconds)
        elapsed = utime.ticks_diff(current_time, self.pairing_mode_start_time)
        if elapsed >= self.pairing_mode_duration_ms:
            self.stop_pairing_mode()
            print("BLE: Pairing mode timed out after 120 seconds")

    def is_pairing_mode(self):
        """Check if currently in pairing mode.

        Returns:
            True if in pairing mode, False otherwise.
        """
        return self.pairing_mode

    def get_pairing_mode_start_time(self):
        """Get pairing mode start time.

        Returns:
            Pairing mode start time in milliseconds, or 0 if not in pairing mode.
        """
        return self.pairing_mode_start_time if self.pairing_mode else 0

    def get_pairing_mode_duration_ms(self):
        """Get pairing mode duration.

        Returns:
            Pairing mode duration in milliseconds.
        """
        return self.pairing_mode_duration_ms
