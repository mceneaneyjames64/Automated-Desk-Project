"""
Comprehensive wrapper for the automated desk controller system.

This module integrates all subsystems:
- Hardware initialization (sensors, I2C, serial)
- Motor control (position control, emergency stop)
- MQTT communication (command handling, feedback publishing)
- Preset management (save/load positions)
- Calibration support
- Heartbeat monitoring
- Logging and status reporting

The DeskControllerWrapper class provides a unified interface for managing
the entire desk system with both synchronous and asynchronous capabilities.
"""

import sys
import time
import json
import os
import threading
from typing import Dict, Optional, Tuple
from enum import Enum
from datetime import datetime

import config
from hardware import (
    init_i2c,
    init_mux,
    scan_i2c_channels,
    init_vl53l0x,
    init_adxl345,
    init_serial,
    get_sensor_value,
)
from motor_control import (
    move_to_distance,
    move_to_angle,
    retract_fully,
    retract_tilt,
    emergency_stop,
)
from calibration import calibrate_vl53_sensors, load_calibration, get_calibrated_reading

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("⚠ paho-mqtt not installed. MQTT features will be unavailable.")


################################################################################
#                           ENUMS & CONSTANTS
################################################################################

class MotorDirection(Enum):
    """Motor movement direction."""
    EXTEND = "extend"
    RETRACT = "retract"
    STOP = "stop"


class SystemState(Enum):
    """System operational state."""
    IDLE = "idle"
    MOVING = "moving"
    CALIBRATING = "calibrating"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class LogLevel(Enum):
    """Logging severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


################################################################################
#                           LOGGING UTILITIES
################################################################################

class DeskLogger:
    """Logging utility with timestamp and level support."""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize logger.
        
        Parameters
        ----------
        log_file : str, optional
            Path to log file. If None, only console output.
        """
        self.log_file = log_file
        self.lock = threading.Lock()
    
    def _format_message(self, level: LogLevel, message: str) -> str:
        """Format log message with timestamp and level."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level.value}] {message}"
    
    def _write(self, formatted: str):
        """Write to console and log file."""
        with self.lock:
            print(formatted)
            if self.log_file:
                try:
                    with open(self.log_file, "a") as f:
                        f.write(formatted + "\n")
                except Exception:
                    pass
    
    def debug(self, message: str):
        """Log debug message."""
        self._write(self._format_message(LogLevel.DEBUG, message))
    
    def info(self, message: str):
        """Log info message."""
        self._write(self._format_message(LogLevel.INFO, message))
    
    def warning(self, message: str):
        """Log warning message."""
        self._write(self._format_message(LogLevel.WARNING, message))
    
    def error(self, message: str):
        """Log error message."""
        self._write(self._format_message(LogLevel.ERROR, message))


class _InterruptibleSerialProxy:
    """Serial proxy that raises when stop is requested."""
    
    def __init__(self, serial_port, stop_event: threading.Event):
        self._serial_port = serial_port
        self._stop_event = stop_event
    
    def write(self, data):
        if self._stop_event.is_set():
            raise InterruptedError("Motor movement interrupted by stop command")
        return self._serial_port.write(data)
    
    def __getattr__(self, attr):
        return getattr(self._serial_port, attr)


################################################################################
#                           DESK CONTROLLER WRAPPER
################################################################################

class DeskControllerWrapper:
    """
    Unified wrapper for the automated desk controller system.
    
    Provides:
    - Hardware initialization and management
    - Motor control with position feedback
    - MQTT integration for Home Assistant
    - Preset management
    - Calibration support
    - System monitoring and logging
    """
    
    def __init__(self, 
                 broker: str = config.MQTT_BROKER,
                 mqtt_port: int = config.MQTT_PORT,
                 mqtt_username: str = config.MQTT_USERNAME,
                 mqtt_password: str = config.MQTT_PASSWORD,
                 mqtt_command_topic: str = "home/desk/command",
                 mqtt_status_topic: str = "home/desk/status",
                 mqtt_feedback_topic: str = "home/desk/feedback",
                 presets_file: str = "desk_presets.json",
                 log_file: Optional[str] = "desk_controller.log"):
        """
        Initialize desk controller wrapper.
        
        Parameters
        ----------
        broker : str
            MQTT broker IP/hostname
        mqtt_port : int
            MQTT broker port
        mqtt_username : str
            MQTT username
        mqtt_password : str
            MQTT password
        mqtt_command_topic : str
            MQTT topic for commands
        mqtt_status_topic : str
            MQTT topic for status messages
        mqtt_feedback_topic : str
            MQTT topic for position feedback
        presets_file : str
            JSON file path for presets
        log_file : str, optional
            Log file path
        """
        # Logger
        self.logger = DeskLogger(log_file)
        
        # Hardware state
        self.sensors = {}
        self.serial_port = None
        self.is_initialized = False
        
        # Motor state (M1 stores angle degrees, M2/M3 store distance millimetres)
        self.motor_positions = {1: None, 2: None, 3: None}
        self.motor_status = {1: "idle", 2: "idle", 3: "idle"}
        self.system_state = SystemState.IDLE
        
        # MQTT state
        self.mqtt_client = None
        self.mqtt_connected = False
        self.mqtt_config = {
            "broker": broker,
            "port": mqtt_port,
            "username": mqtt_username,
            "password": mqtt_password,
            "command_topic": mqtt_command_topic,
            "status_topic": mqtt_status_topic,
            "feedback_topic": mqtt_feedback_topic,
        }
        
        # Preset state
        self.presets_file = presets_file
        self.presets = {
            1: {1: None, 2: None, 3: None},
            2: {1: None, 2: None, 3: None},
            3: {1: None, 2: None, 3: None},
        }
        
        # Calibration state
        self.calibration_data = load_calibration()
        
        # Thread-safety locks.
        # position_lock  – guards motor_positions (read/written from the motor
        #                  worker thread and the MQTT callback thread).
        # mqtt_lock      – serialises mqtt_client.publish() calls so that
        #                  concurrent feedback publications don't interleave.
        # motor_command_lock – binary semaphore that prevents two motor
        #                  movements from running at the same time; acquired
        #                  before starting a worker thread and released inside
        #                  _run_motor_worker when the task finishes.
        # motor_stop_event – threading.Event that _InterruptibleSerialProxy
        #                  polls on every write; set by emergency_stop_all()
        #                  to interrupt any in-progress movement immediately.
        self.position_lock = threading.Lock()
        self.mqtt_lock = threading.Lock()
        self.motor_command_lock = threading.Lock()
        self.motor_stop_event = threading.Event()
        
        self.logger.info("DeskControllerWrapper initialized")
    
    ################################################################################
    #                           HARDWARE INITIALIZATION
    ################################################################################
    
    def initialize_hardware(self) -> bool:
        """
        Initialize all hardware components.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            self.logger.info("Initializing hardware...")
            
            # Initialize I2C
            i2c = init_i2c()
            
            # Initialize multiplexer
            tca = init_mux(i2c)
            self.sensors[config.SENSOR_MUX] = tca
            
            # Scan I2C channels
            scan_i2c_channels(tca)
            
            # Initialize VL53L0X sensors
            self.sensors[config.SENSOR_VL53_0] = init_vl53l0x(
                tca, config.VL53_CHANNEL_1, "VL53L0X #0"
            )
            self.sensors[config.SENSOR_VL53_1] = init_vl53l0x(
                tca, config.VL53_CHANNEL_2, "VL53L0X #1"
            )
            
            # Initialize ADXL345
            self.sensors[config.SENSOR_ADXL] = init_adxl345(tca)
            
            # Initialize serial port
            self.serial_port = init_serial()
            
            # Load calibration data
            self.calibration_data = load_calibration()
            if self.calibration_data:
                self.logger.info("Calibration data loaded")
            else:
                self.logger.warning("No calibration data found")
            
            self.is_initialized = True
            self.logger.info("✓ Hardware initialized successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Hardware initialization failed: {e}")
            self.system_state = SystemState.ERROR
            return False
    
    ################################################################################
    #                           SENSOR READING
    ################################################################################
    
    def read_sensor_raw(self, sensor_name: str) -> Optional[float]:
        """
        Read raw sensor value.
        
        Parameters
        ----------
        sensor_name : str
            Sensor name constant from config
        
        Returns
        -------
        float or None
            Raw sensor reading in mm, or None on error
        """
        try:
            if not self.is_initialized:
                self.logger.warning("Hardware not initialized")
                return None
            
            value = get_sensor_value(self.sensors, sensor_name)
            return value
        
        except Exception as e:
            self.logger.error(f"Error reading sensor {sensor_name}: {e}")
            return None
    
    def read_sensor_calibrated(self, sensor_name: str) -> Optional[float]:
        """
        Read calibrated (offset-corrected) sensor value.
        
        Parameters
        ----------
        sensor_name : str
            Sensor name constant from config
        
        Returns
        -------
        float or None
            Calibrated sensor reading in mm, or None on error
        """
        try:
            if not self.is_initialized:
                self.logger.warning("Hardware not initialized")
                return None
            
            if not self.calibration_data:
                self.logger.warning("No calibration data available")
                return self.read_sensor_raw(sensor_name)
            
            reading = get_calibrated_reading(self.sensors, sensor_name, self.calibration_data)
            return reading["corrected_mm"]
        
        except Exception as e:
            self.logger.error(f"Error reading calibrated sensor {sensor_name}: {e}")
            return self.read_sensor_raw(sensor_name)
    
    ################################################################################
    #                           MOTOR CONTROL
    ################################################################################

    def _motor_unit(self, motor_id: int) -> str:
        """Return display/storage unit for a motor target/position."""
        return "deg" if motor_id == 1 else "mm"

    def _motor_max_target(self, motor_id: int) -> float:
        """Return maximum allowed target for motor_id in its native unit."""
        return config.MAX_ANGLE_DEG if motor_id == 1 else config.MAX_POSITION

    def _motor_min_target(self, motor_id: int) -> float:
        """Return minimum allowed target for motor_id in its native unit."""
        return config.MIN_ANGLE_DEG if motor_id == 1 else config.MIN_POSITION

    def _distance_sensor_for_motor(self, motor_id: int) -> Optional[str]:
        """Return VL53 sensor name for distance motors (M2/M3), else None."""
        return {
            2: config.SENSOR_VL53_0,
            3: config.SENSOR_VL53_1,
        }.get(motor_id)
    
    def _run_motor_worker(self, task_name: str, task_fn, *args):
        """Execute a motor task and release the command lock when done.

        Runs on a dedicated background daemon thread started by
        _start_motor_worker.  Ensures motor_command_lock is always released
        even if the task raises an exception, preventing the controller from
        getting stuck in a "busy" state.
        """
        try:
            self.logger.debug(f"Motor worker '{task_name}' starting on thread {threading.current_thread().name}")
            task_fn(*args)
            self.logger.debug(f"Motor worker '{task_name}' completed successfully")
        except Exception as e:
            self.logger.error(f"Motor worker '{task_name}' failed: {e}")
        finally:
            self.motor_command_lock.release()
            self.logger.debug(f"Motor command lock released by worker '{task_name}'")
    
    def _reject_if_calibrating(self, publish_status: bool = False) -> bool:
        """Return True when movement should be rejected due to calibration state."""
        if self.system_state != SystemState.CALIBRATING:
            return False

        self.logger.warning("Cannot move motors during calibration")
        if publish_status:
            self.publish_status("calibrating")
        return True

    def _start_motor_worker(self, task_name: str, task_fn, *args) -> bool:
        """Start a worker thread for motor operations.

        Attempts a non-blocking acquire of motor_command_lock so that only
        one actuator operation runs at a time.  If the lock is already held
        (another motor is moving) the command is rejected and False is
        returned.  On success, motor_stop_event is cleared so that
        _InterruptibleSerialProxy allows serial writes through, and a daemon
        thread is spawned to run the task.
        """
        if not self.motor_command_lock.acquire(blocking=False):
            self.logger.warning(f"Ignoring '{task_name}' command: motor_command_lock already held (another motor is moving)")
            self.publish_status("busy")
            return False
        
        self.logger.debug(f"Motor command lock acquired for task '{task_name}'")
        self.motor_stop_event.clear()
        
        worker = threading.Thread(
            target=self._run_motor_worker,
            args=(task_name, task_fn, *args),
            daemon=True,
            name=f"motor-worker-{task_name}",
        )
        
        try:
            worker.start()
            self.logger.debug(f"Motor worker thread started for '{task_name}'")
        except Exception:
            self.motor_command_lock.release()
            self.logger.error(f"Failed to start motor worker thread for '{task_name}'")
            raise
        
        return True

    def _start_motor_movement_worker(self, task_name: str, task_fn, *args) -> bool:
        """Start a motor movement worker while enforcing calibration interlock."""
        if self._reject_if_calibrating(publish_status=True):
            return False
        return self._start_motor_worker(task_name, task_fn, *args)

    def _run_calibration_worker(self) -> bool:
        """Run calibration and publish MQTT status updates."""
        self.publish_status("Starting calibration")
        success = self.run_calibration()
        self.publish_status("Calibration complete" if success else "Calibration failed")
        return success
    
    def move_motor_to_position(self, motor_id: int, target_value: float,
                               tolerance: int = 2, timeout: float = 30) -> bool:
        """
        Move a motor to a specific position.
        
        Parameters
        ----------
        motor_id : int
            Motor ID (1-3)
        target_value : float
            Target value (degrees for M1, millimeters for M2/M3)
        tolerance : int
            Acceptable error (degrees for M1, mm for M2/M3)
        timeout : float
            Maximum movement time in seconds
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if not self.is_initialized:
                self.logger.warning("Hardware not initialized")
                return False

            if self._reject_if_calibrating():
                return False
            
            if motor_id not in [1, 2, 3]:
                self.logger.error(f"Invalid motor ID: {motor_id}")
                return False
            
            unit = self._motor_unit(motor_id)
            self.logger.info(f"Moving motor {motor_id} to {target_value} {unit}")
            self.motor_status[motor_id] = "moving"
            self.system_state = SystemState.MOVING
            self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
            
            serial_port = _InterruptibleSerialProxy(self.serial_port, self.motor_stop_event)
            if motor_id == 1:
                success = move_to_angle(
                    self.sensors,
                    target_value,
                    serial_port,
                    tolerance=tolerance,
                    timeout=timeout,
                )
            else:
                sensor_name = self._distance_sensor_for_motor(motor_id)
                if not sensor_name:
                    self.logger.error(f"No sensor mapped for motor {motor_id}")
                    return False
                success = move_to_distance(
                    self.sensors,
                    sensor_name,
                    target_value,
                    serial_port,
                    tolerance=tolerance,
                    timeout=timeout,
                )
            
            if success:
                with self.position_lock:
                    self.motor_positions[motor_id] = target_value
                self.motor_status[motor_id] = "idle"
                self.logger.info(f"✓ Motor {motor_id} reached {target_value} {unit}")
                self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
                
                # Publish feedback
                self.publish_position_feedback(motor_id)
                
                # Update system state if all motors are idle
                if all(status == "idle" for status in self.motor_status.values()):
                    self.system_state = SystemState.IDLE
                
                return True
            else:
                self.motor_status[motor_id] = "error"
                self.system_state = SystemState.ERROR
                self.logger.error(f"✗ Motor {motor_id} failed to reach {target_value} {unit}")
                self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
                return False
        
        except InterruptedError:
            self.motor_status[motor_id] = "stopped"
            if all(status != "moving" for status in self.motor_status.values()):
                self.system_state = SystemState.IDLE
            self.logger.warning(f"Motor {motor_id} movement interrupted")
            self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
            return False
        
        except Exception as e:
            self.logger.error(f"Error moving motor {motor_id}: {e}")
            self.motor_status[motor_id] = "error"
            self.system_state = SystemState.ERROR
            self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
            return False
    
    def retract_motor_fully(self, motor_id: int, timeout: float = 30) -> bool:
        """
        Retract a motor to minimum position.
        
        Parameters
        ----------
        motor_id : int
            Motor ID (1-3)
        timeout : float
            Maximum movement time in seconds
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if not self.is_initialized:
                self.logger.warning("Hardware not initialized")
                return False

            if self._reject_if_calibrating():
                return False
            
            if motor_id not in [1, 2, 3]:
                self.logger.error(f"Invalid motor ID: {motor_id}")
                return False
            
            self.logger.info(f"Retracting motor {motor_id} to minimum position")
            self.motor_status[motor_id] = "moving"
            self.system_state = SystemState.MOVING
            self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
            
            serial_port = _InterruptibleSerialProxy(self.serial_port, self.motor_stop_event)
            if motor_id == 1:
                success = retract_tilt(self.sensors, serial_port, timeout=timeout)
            else:
                sensor_name = self._distance_sensor_for_motor(motor_id)
                if not sensor_name:
                    self.logger.error(f"No sensor mapped for motor {motor_id}")
                    return False
                success = retract_fully(self.sensors, sensor_name, serial_port, timeout=timeout)
            
            if success:
                with self.position_lock:
                    self.motor_positions[motor_id] = self._motor_min_target(motor_id)
                self.motor_status[motor_id] = "idle"
                self.logger.info(f"✓ Motor {motor_id} fully retracted")
                self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
                
                # Publish feedback
                self.publish_position_feedback(motor_id)
                
                if all(status == "idle" for status in self.motor_status.values()):
                    self.system_state = SystemState.IDLE
                
                return True
            else:
                self.motor_status[motor_id] = "error"
                self.system_state = SystemState.ERROR
                self.logger.error(f"✗ Motor {motor_id} failed to retract")
                self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
                return False
        
        except InterruptedError:
            self.motor_status[motor_id] = "stopped"
            if all(status != "moving" for status in self.motor_status.values()):
                self.system_state = SystemState.IDLE
            self.logger.warning(f"Motor {motor_id} retraction interrupted")
            self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
            return False
        
        except Exception as e:
            self.logger.error(f"Error retracting motor {motor_id}: {e}")
            self.motor_status[motor_id] = "error"
            self.system_state = SystemState.ERROR
            self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
            return False
    
    def emergency_stop_all(self) -> bool:
        """
        Emergency stop all motors.

        Sets motor_stop_event, which causes _InterruptibleSerialProxy to raise
        InterruptedError on the very next serial write inside any running motor
        worker thread.  The hardware CMD_ALL_OFF command is then sent directly
        on the real serial port (bypassing the proxy) so the actuators halt
        even if no worker thread is currently active.

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            self.logger.warning("EMERGENCY STOP - All motors disabled")
            self.motor_stop_event.set()
            emergency_stop(self.serial_port)
            
            for motor_id in [1, 2, 3]:
                self.motor_status[motor_id] = "stopped"
                self.logger.debug(f"M{motor_id} status: {self.motor_status[motor_id]}")
            
            self.system_state = SystemState.IDLE
            self.publish_status("EMERGENCY STOP")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
            return False
    
    ################################################################################
    #                           PRESET MANAGEMENT
    ################################################################################
    
    def load_presets_from_file(self) -> bool:
        """
        Load presets from JSON file.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, "r") as f:
                    data = json.load(f)
                    self.presets = {
                        int(p): {int(m): v for m, v in motors.items()}
                        for p, motors in data.items()
                    }
                self.logger.info(f"✓ Presets loaded from {self.presets_file}")
                return True
            else:
                self.logger.info(f"No preset file found at {self.presets_file}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error loading presets: {e}")
            return False
    
    def save_presets_to_file(self) -> bool:
        """
        Save presets to JSON file.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            with open(self.presets_file, "w") as f:
                json.dump(self.presets, f, indent=4)
            self.logger.info(f"✓ Presets saved to {self.presets_file}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving presets: {e}")
            return False
    
    def save_current_position_as_preset(self, preset_id: int) -> bool:
        """
        Save current motor positions as a preset by reading all sensors directly.

        Reads fresh calibrated sensor values for all three motors instead of
        relying on cached motor_positions:
        - Motor 1 (M1): ADXL345 tilt angle via config.SENSOR_ADXL
        - Motor 2 (M2): VL53L0X #0 distance via config.SENSOR_VL53_0
        - Motor 3 (M3): VL53L0X #1 distance via config.SENSOR_VL53_1

        Parameters
        ----------
        preset_id : int
            Preset ID (1-3)

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if preset_id not in self.presets:
                self.logger.error(f"Invalid preset ID: {preset_id}")
                return False

            self.logger.info(f"Reading all sensors for preset {preset_id}...")

            # Read calibrated sensor values for all three motors
            sensor_readings = {
                1: self.read_sensor_calibrated(config.SENSOR_ADXL),
                2: self.read_sensor_calibrated(config.SENSOR_VL53_0),
                3: self.read_sensor_calibrated(config.SENSOR_VL53_1),
            }

            # Verify all readings are valid
            failed_motors = [m_id for m_id, reading in sensor_readings.items() if reading is None]
            if failed_motors:
                self.logger.error(
                    f"Cannot save preset {preset_id}: failed to read sensors for motors {failed_motors}"
                )
                return False

            # Update motor_positions with fresh readings and save preset
            with self.position_lock:
                self.motor_positions.update(sensor_readings)
                self.presets[preset_id] = sensor_readings.copy()

            self.save_presets_to_file()
            self.logger.info(f"✓ Preset {preset_id} saved: {self.presets[preset_id]}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving preset {preset_id}: {e}")
            return False
    
    def load_and_execute_preset(self, preset_id: int) -> bool:
        """
        Load and execute a preset.

        Motors are moved one at a time in the required order:
          1. Motor 2 – keyboard height  (VL53L0X #0)
          2. Motor 3 – monitor height   (VL53L0X #1)
          3. Motor 1 – monitor tilt     (ADXL345)

        An emergency stop can interrupt the sequence at any point.

        Parameters
        ----------
        preset_id : int
            Preset ID (1-3)

        Returns
        -------
        bool
            True if all motors reached their target, False otherwise
        """
        try:
            if preset_id not in self.presets:
                self.logger.error(f"Invalid preset ID: {preset_id}")
                return False

            preset = self.presets[preset_id]

            # Validate that all positions are set
            if None in preset.values():
                self.logger.error(f"Preset {preset_id} is not fully configured")
                return False

            self.logger.info(f"Loading preset {preset_id}: {preset}")
            self.system_state = SystemState.MOVING

            # Required movement order: keyboard height → monitor height → monitor tilt
            all_success = True
            for motor_id in [2, 3, 1]:
                # Allow emergency stop to abort between motor movements
                if self.motor_stop_event.is_set():
                    self.logger.warning(f"Preset {preset_id} interrupted by emergency stop")
                    self.system_state = SystemState.IDLE
                    return False

                target_pos = preset[motor_id]
                unit = self._motor_unit(motor_id)
                self.logger.info(f"  Moving motor {motor_id} to {target_pos} {unit}")

                success = self.move_motor_to_position(motor_id, target_pos)
                if not success:
                    all_success = False
                    self.logger.error(
                        f"  ✗ Motor {motor_id} failed to reach {target_pos} {unit}"
                    )
                    # If the failure was caused by an emergency stop, exit immediately
                    if self.motor_stop_event.is_set():
                        self.logger.warning(f"Preset {preset_id} interrupted by emergency stop")
                        self.system_state = SystemState.IDLE
                        return False

            if all_success:
                self.logger.info(f"✓ Preset {preset_id} executed successfully")
                self.system_state = SystemState.IDLE
            else:
                self.logger.error(f"✗ Preset {preset_id} execution failed")
                self.system_state = SystemState.ERROR

            return all_success

        except Exception as e:
            self.logger.error(f"Error loading preset {preset_id}: {e}")
            self.system_state = SystemState.ERROR
            return False
    
    ################################################################################
    #                           CALIBRATION
    ################################################################################
    
    def run_calibration(self) -> bool:
        """
        Run sensor calibration routine.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if not self.is_initialized:
                self.logger.warning("Hardware not initialized")
                return False
            
            self.system_state = SystemState.CALIBRATING
            self.logger.info("Starting sensor calibration...")
            
            calibration_data = calibrate_vl53_sensors(self.sensors)
            self.calibration_data = calibration_data
            
            self.logger.info("✓ Calibration complete")
            self.system_state = SystemState.IDLE
            return True
        
        except Exception as e:
            self.logger.error(f"Calibration failed: {e}")
            self.system_state = SystemState.ERROR
            return False
    
    ################################################################################
    #                           MQTT INTEGRATION
    ################################################################################
    
    def mqtt_connect(self) -> bool:
        """
        Connect to MQTT broker.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        if not MQTT_AVAILABLE:
            self.logger.warning("MQTT not available (paho-mqtt not installed)")
            return False
        
        try:
            # Use VERSION1 (not VERSION2) to support standard callback signatures
            # VERSION2 requires different callback parameters
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            
            self.mqtt_client.on_connect = self._mqtt_on_connect
            self.mqtt_client.on_message = self._mqtt_on_message
            self.mqtt_client.on_disconnect = self._mqtt_on_disconnect
            
            self.mqtt_client.username_pw_set(
                self.mqtt_config["username"],
                self.mqtt_config["password"]
            )
            
            # Set keepalive to 60 seconds (default is 60, but being explicit)
            self.mqtt_client.connect(
                self.mqtt_config["broker"],
                self.mqtt_config["port"],
                keepalive=60
            )
            
            self.mqtt_client.loop_start()
            self.logger.info(f"✓ MQTT connection initiated to {self.mqtt_config['broker']}")
            return True
        
        except Exception as e:
            self.logger.error(f"MQTT connection failed: {e}")
            return False
    
    def mqtt_disconnect(self) -> bool:
        """
        Disconnect from MQTT broker.
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if self.mqtt_client is not None:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                self.mqtt_connected = False
                self.logger.info("✓ MQTT disconnected")
                return True
            return False
        
        except Exception as e:
            self.logger.error(f"Error disconnecting MQTT: {e}")
            return False
    
    def _mqtt_on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            with self.mqtt_lock:
                self.mqtt_connected = True
            self.logger.info(f"✓ MQTT connected (return code: {rc})")
            client.subscribe(self.mqtt_config["command_topic"], 1)
        else:
            self.logger.error(f"✗ MQTT connection refused (return code: {rc})")
    
    def _mqtt_on_message(self, client, userdata, message):
        """MQTT message callback.

        Routes incoming command payloads to the appropriate handler.  All
        motor-movement commands are dispatched to background worker threads
        (via _start_motor_movement_worker) so that this callback returns
        immediately and does not block the MQTT network loop.

        Routing order (first match wins):
          "Heartbeat"           – publish heartbeat_ok status.
          "Feedback{N}:{v}"    – update cached motor position under position_lock.
          "m{N} -> up|down|…"  – start a motor movement worker.
          "save preset {N}"    – save current sensor readings as preset N.
          "preset {N}"         – execute preset N in a worker thread.
          "preset_{word}"      – execute named preset (one/two/three).
          "set_preset_{word}"  – save named preset.
          "emergency_stop"     – halt all motors immediately.
          "calibrate"          – run calibration in a worker thread.
        """
        try:
            payload = message.payload.decode().strip()
            self.logger.debug(f"MQTT message received: {payload}")
            
            # Handle different command types
            if payload == "Heartbeat":
                self.publish_status("heartbeat_ok")
            
            elif payload.startswith("Feedback"):
                # Position feedback from motor controller
                for motor_id in [1, 2, 3]:
                    if payload.startswith(f"Feedback{motor_id}:"):
                        value_str = payload[len(f"Feedback{motor_id}:"):].strip()
                        try:
                            position = float(value_str)
                            with self.position_lock:
                                self.motor_positions[motor_id] = position
                            self.logger.debug(f"Position updated - M{motor_id}: {position}")
                        except ValueError:
                            pass
                        break
            
            elif " -> " in payload:
                # Motor command: "m{id} -> {direction|position}"
                parts = payload.split("->")
                motor_part = parts[0].strip()
                direction_part = parts[1].strip()
                
                if motor_part.startswith("m"):
                    motor_id = int(motor_part[1:])
                    
                    if direction_part.lower() == "up":
                        target = self._motor_max_target(motor_id)
                        self._start_motor_movement_worker(
                            f"m{motor_id}-up",
                            self.move_motor_to_position,
                            motor_id,
                            target
                        )
                    elif direction_part.lower() == "down":
                        self._start_motor_movement_worker(
                            f"m{motor_id}-down",
                            self.retract_motor_fully,
                            motor_id
                        )
                    elif direction_part.lower() == "stop":
                        self.emergency_stop_all()
                    else:
                        try:
                            target_pos = float(direction_part)
                            self._start_motor_movement_worker(
                                f"m{motor_id}-move",
                                self.move_motor_to_position,
                                motor_id,
                                target_pos
                            )
                        except ValueError:
                            self.logger.warning(f"Could not parse motor target position from: {payload}")
            
            elif payload.startswith("save preset "):
                # Preset save: "save preset 1", "save preset 2", "save preset 3"
                try:
                    preset_id = int(payload.split()[-1])
                    if preset_id in self.presets:
                        self.save_current_position_as_preset(preset_id)
                    else:
                        self.logger.warning(f"Invalid preset ID in message: {payload}")
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse preset ID from message: {payload}")

            elif payload.startswith("preset "):
                # Preset load: "preset 1", "preset 2", "preset 3"
                try:
                    preset_id = int(payload.split()[-1])
                    if preset_id in self.presets:
                        self._start_motor_worker(
                            f"preset-{preset_id}",
                            self.load_and_execute_preset,
                            preset_id,
                        )
                    else:
                        self.logger.warning(f"Invalid preset ID in message: {payload}")
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse preset ID from message: {payload}")

            elif payload.startswith("preset_") and not payload.endswith("_save"):
                # Preset load: "preset_one", "preset_two", "preset_three"
                preset_names = {"one": 1, "two": 2, "three": 3}
                preset_word = payload.split("_")[1]
                preset_id = preset_names.get(preset_word)
                if preset_id:
                    self._start_motor_worker(
                        f"preset-{preset_id}",
                        self.load_and_execute_preset,
                        preset_id
                    )

            elif payload.startswith("set_preset_"):
                # Preset save: "set_preset_one", "set_preset_two", "set_preset_three"
                preset_names = {"one": 1, "two": 2, "three": 3}
                preset_word = payload.split("_")[-1]
                preset_id = preset_names.get(preset_word)
                if preset_id:
                    self.save_current_position_as_preset(preset_id)
            
            elif payload == "emergency_stop":
                self.emergency_stop_all()

            elif payload == "calibrate":
                self._start_motor_worker(
                    "calibrate",
                    self._run_calibration_worker,
                )
        
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def _mqtt_on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        with self.mqtt_lock:
            self.mqtt_connected = False
        self.logger.warning(f"MQTT disconnected (return code: {rc})")
    
    def publish_status(self, message: str) -> bool:
        """
        Publish status message.
        
        Parameters
        ----------
        message : str
            Status message
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        if not self.mqtt_connected or self.mqtt_client is None:
            return False
        
        try:
            with self.mqtt_lock:
                self.mqtt_client.publish(
                    self.mqtt_config["status_topic"],
                    message
                )
            return True
        except Exception as e:
            self.logger.error(f"Error publishing status: {e}")
            return False
    
    def publish_position_feedback(self, motor_id: int) -> bool:
        """
        Publish position feedback for a motor.

        Called immediately after each successful motor movement so that the
        MQTT broker (and any subscribers such as Home Assistant) receive an
        up-to-date position reading without waiting for a periodic poll.

        Parameters
        ----------
        motor_id : int
            Motor ID (1-3)
        
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        if not self.mqtt_connected or self.mqtt_client is None:
            return False
        
        try:
            with self.position_lock:
                position = self.motor_positions.get(motor_id)
            
            if position is None:
                return False
            
            topic = f"{self.mqtt_config['feedback_topic']}/motor{motor_id}"
            payload = f"Feedback{motor_id}:{position}"
            
            with self.mqtt_lock:
                self.mqtt_client.publish(topic, payload)
            
            return True
        except Exception as e:
            self.logger.error(f"Error publishing feedback for M{motor_id}: {e}")
            return False
    
    def publish_all_position_feedback(self) -> bool:
        """
        Publish position feedback for all motors.

        Publishes the current position of all three motors to their respective
        MQTT feedback topics. This is typically called by the heartbeat loop
        to keep Home Assistant or other subscribers updated with the latest
        motor positions.

        Returns
        -------
        bool
            True if all motors published successfully, False otherwise
        """
        try:
            if not self.mqtt_connected or self.mqtt_client is None:
                return False
            
            all_success = True
            for motor_id in [1, 2, 3]:
                if not self.publish_position_feedback(motor_id):
                    all_success = False
            
            return all_success
        
        except Exception as e:
            self.logger.error(f"Error publishing all position feedback: {e}")
            return False
    
    ################################################################################
    #                           STATUS & MONITORING
    ################################################################################
    
    def get_system_status(self) -> Dict:
        """
        Get current system status.
        
        Returns
        -------
        dict
            System status dictionary
        """
        with self.position_lock:
            positions = self.motor_positions.copy()
        
        return {
            "initialized": self.is_initialized,
            "system_state": self.system_state.value,
            "motor_positions": positions,
            "motor_status": self.motor_status.copy(),
            "mqtt_connected": self.mqtt_connected,
            "motor_lock_held": self.motor_command_lock.locked(),
            "timestamp": datetime.now().isoformat(),
        }
    
    def print_system_status(self):
        """Print system status to console."""
        status = self.get_system_status()
        
        print("\n" + "="*60)
        print("  DESK CONTROLLER STATUS")
        print("="*60)
        print(f"Initialized:      {status['initialized']}")
        print(f"System State:     {status['system_state']}")
        print(f"MQTT Connected:   {status['mqtt_connected']}")
        print(f"Motor Lock Held:  {status['motor_lock_held']}")
        print(f"\nMotor Positions:")
        for motor_id, position in status['motor_positions'].items():
            status_str = status['motor_status'].get(motor_id, "unknown")
            pos_str = (
                f"{position:.1f} {self._motor_unit(motor_id)}"
                if position is not None else "unknown"
            )
            print(f"  M{motor_id}: {pos_str:15} [{status_str}]")
        print(f"\nTimestamp:        {status['timestamp']}")
        print("="*60 + "\n")
    
    ################################################################################
    #                           SHUTDOWN
    ################################################################################
    
    def shutdown(self):
        """Shutdown the controller gracefully."""
        try:
            self.logger.info("Shutting down controller...")
            
            # Stop motors
            self.emergency_stop_all()
            
            # Disconnect MQTT
            if self.mqtt_connected:
                self.mqtt_disconnect()
            
            # Close serial port
            if self.serial_port is not None:
                try:
                    self.serial_port.write(config.CMD_ALL_OFF)
                    self.serial_port.close()
                    self.logger.info("Serial port closed")
                except Exception:
                    pass
            
            self.logger.info("✓ Shutdown complete")
        
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


################################################################################
#                           EXAMPLE USAGE
################################################################################

def main():
    """Example usage of the desk controller wrapper."""
    
    print("\n" + "="*70)
    print("  AUTOMATED DESK CONTROLLER - INTEGRATED WRAPPER")
    print("="*70 + "\n")
    
    # Create controller
    controller = DeskControllerWrapper(
        log_file="desk_controller.log"
    )
    
    try:
        # Initialize hardware
        if not controller.initialize_hardware():
            print("✗ Failed to initialize hardware")
            return 1
        
        # Load presets
        controller.load_presets_from_file()
        
        # Connect to MQTT
        controller.mqtt_connect()
        
        # Print status
        controller.print_system_status()
        
        # Example: Move motor 1 to 200 degrees
        print("Example: Moving motor 1 to 200 degrees...")
        if controller.move_motor_to_position(1, 200):
            print("✓ Motor 1 moved successfully")
        
        # Example: Save current position as preset 1
        print("\nExample: Saving current position as preset 1...")
        if controller.save_current_position_as_preset(1):
            print("✓ Preset 1 saved")
        
        # Print final status
        controller.print_system_status()
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n✓ Interrupted by user")
        return 0
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    finally:
        controller.shutdown()


if __name__ == "__main__":
    sys.exit(main())
