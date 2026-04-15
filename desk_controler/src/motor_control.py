"""
Motor control functions for actuator positioning.

Distance actuators (Motors 1 & 2)
----------------------------------
  move_to_distance()  — closed-loop control using VL53L0X sensors (mm).
  retract_fully()     — drives an actuator to config.MIN_POSITION.

Angle actuator (Motor 3)
------------------------
  move_to_angle()     — closed-loop control using the ADXL345 accelerometer
                        (degrees).  Reads the Z-axis tilt angle as returned
                        by get_sensor_value(sensors, config.SENSOR_ADXL):

                            0°   → sensor upside down   (Z ≈ −g)
                            90°  → sensor perpendicular  (Z ≈  0)
                            180° → sensor right-side up  (Z ≈ +g)

  retract_tilt()      — drives the angle actuator to config.MIN_ANGLE_DEG.

Emergency stop
--------------
  emergency_stop()    — immediately halts all motors.

Offset correction
-----------------
config.OFFSET stores a per-sensor software offset (float, mm) produced by
the VL53L0X calibration routine.  All distance movement loops call
_read_corrected() so the offset is applied in exactly one place.

The ADXL345 does not use a software offset — the angle is computed directly
from the Z-axis gravity vector, which is self-referencing.
"""

import time

import config
from hardware import get_sensor_value


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_motor_commands(sensor_name: str) -> dict:
    """Return the {'extend': bytes, 'retract': bytes} dict for sensor_name."""
    try:
        return config.SENSOR_MOTOR_COMMANDS[sensor_name]
    except KeyError:
        valid = list(config.SENSOR_MOTOR_COMMANDS.keys())
        raise ValueError(
            f"No motor commands defined for sensor '{sensor_name}'. "
            f"Valid sensors: {valid}"
        )


def _read_corrected(sensors: dict, sensor_name: str) -> float:
    """
    Return the offset-corrected distance for a VL53L0X sensor.

    Applies config.OFFSET[sensor_name] to the raw reading.  If no offset
    entry exists (calibration not yet run) the raw reading is returned and a
    warning is printed.
    """
    raw = get_sensor_value(sensors, sensor_name)
    offset = getattr(config, "OFFSET", {}).get(sensor_name)
    if offset is None:
        print(f"[motor] Warning: no calibration offset for '{sensor_name}' — "
              f"using raw reading.")
        return raw
    return raw + offset


# ---------------------------------------------------------------------------
# Distance actuators (VL53L0X feedback)
# ---------------------------------------------------------------------------

def move_to_distance(sensors: dict, sensor_name: str, target_mm: float,
                     ser, tolerance: int = 2, timeout: float = 30) -> bool:
    """
    Move an actuator until its corrected sensor reading reaches target_mm.

    Parameters
    ----------
    sensors     : Dictionary of initialised sensor objects.
    sensor_name : One of config.SENSOR_VL53_0 / SENSOR_VL53_1.
    target_mm   : Desired true distance in millimetres.
    ser         : Open serial.Serial object.
    tolerance   : Acceptable error in mm (default ±2 mm).
    timeout     : Maximum movement time in seconds (default 30 s).

    Returns
    -------
    True if the target was reached, False on timeout.
    """
    if ser is None:
        raise ValueError("A serial port object is required for motor control.")

    motor_cmds  = _get_motor_commands(sensor_name)
    cmd_extend  = motor_cmds["extend"]
    cmd_retract = motor_cmds["retract"]

    clamped_mm = max(config.MIN_POSITION, min(config.MAX_POSITION, target_mm))
    if clamped_mm != target_mm:
        print(f"[motor] Position {target_mm} mm clamped to {clamped_mm} mm "
              f"(limits: {config.MIN_POSITION}–{config.MAX_POSITION} mm).")

    print(f"[motor] Moving '{sensor_name}' → {clamped_mm} mm  (±{tolerance} mm)")

    start_time = time.monotonic()

    while True:
        if time.monotonic() - start_time > timeout:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] Timeout after {timeout} s — motion aborted.")
            return False

        current_mm = _read_corrected(sensors, sensor_name)
        error      = current_mm - clamped_mm

        if abs(error) <= tolerance:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] Target reached: {current_mm:.1f} mm "
                  f"(target {clamped_mm} mm).")
            return True

        # Positive error → too far out → retract
        # Negative error → not far enough → extend
        ser.write(cmd_retract if error > 0 else cmd_extend)
        time.sleep(0.05)


def retract_fully(sensors: dict, sensor_name: str,
                  ser, timeout: float = 30) -> bool:
    """
    Drive an actuator to config.MIN_POSITION using corrected sensor readings.

    Parameters
    ----------
    sensors     : Dictionary of initialised sensor objects.
    sensor_name : One of config.SENSOR_VL53_0 / SENSOR_VL53_1.
    ser         : Open serial.Serial object.
    timeout     : Maximum movement time in seconds (default 30 s).

    Returns
    -------
    True if fully retracted, False on timeout.
    """
    if ser is None:
        raise ValueError("A serial port object is required for motor control.")

    cmd_retract = _get_motor_commands(sensor_name)["retract"]

    print(f"[motor] Retracting '{sensor_name}' to minimum position "
          f"({config.MIN_POSITION} mm) …")

    start_time = time.monotonic()

    while time.monotonic() - start_time < timeout:
        current_mm = _read_corrected(sensors, sensor_name)

        if current_mm <= config.MIN_POSITION:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] '{sensor_name}' retracted to {current_mm:.1f} mm.")
            return True

        ser.write(cmd_retract)
        time.sleep(0.1)

    ser.write(config.CMD_ALL_OFF)
    print(f"[motor] Timeout while retracting '{sensor_name}'.")
    return False


# ---------------------------------------------------------------------------
# Angle actuator (ADXL345 feedback, Motor 3)
# ---------------------------------------------------------------------------

def move_to_angle(sensors: dict, target_deg: float,
                  ser, tolerance: float = 1.0, timeout: float = 30) -> bool:
    """
    Move the tilt actuator (Motor 3) to a target angle using the ADXL345.

    The ADXL345 measures tilt via the Z-axis gravity component.  The angle
    convention (set in sensors.get_sensor_value) is:

        0°   → sensor upside down    (Z ≈ −g)
        90°  → sensor perpendicular  (Z ≈  0)
        180° → sensor right-side up  (Z ≈ +g)

    The actuator stroke is 200 mm.  Angle limits are enforced by
    config.MIN_ANGLE_DEG and config.MAX_ANGLE_DEG so the actuator never
    travels beyond its physical range.

    Direction logic
    ---------------
    The relationship between extension direction and angle change depends on
    how the actuator is mounted.  This implementation assumes:

        Extending the actuator  → angle increases
        Retracting the actuator → angle decreases

    If your installation is inverted, swap cmd_extend and cmd_retract below.

    Parameters
    ----------
    sensors    : Dictionary of initialised sensor objects.
    target_deg : Desired tilt angle in degrees.
    ser        : Open serial.Serial object.
    tolerance  : Acceptable error in degrees (default ±1.0°).
    timeout    : Maximum movement time in seconds (default 30 s).

    Returns
    -------
    True if the target angle was reached, False on timeout.
    """
    if ser is None:
        raise ValueError("A serial port object is required for motor control.")

    motor_cmds  = _get_motor_commands(config.SENSOR_ADXL)
    cmd_extend  = motor_cmds["extend"]
    cmd_retract = motor_cmds["retract"]

    # Clamp target to safe range
    clamped_deg = max(config.MIN_ANGLE_DEG, min(config.MAX_ANGLE_DEG, target_deg))
    if clamped_deg != target_deg:
        print(f"[motor] Angle {target_deg:.1f}° clamped to {clamped_deg:.1f}° "
              f"(limits: {config.MIN_ANGLE_DEG}°–{config.MAX_ANGLE_DEG}°).")

    print(f"[motor] Moving tilt actuator → {clamped_deg:.1f}°  (±{tolerance}°)")

    start_time = time.monotonic()

    while True:
        if time.monotonic() - start_time > timeout:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] Tilt timeout after {timeout} s — motion aborted.")
            return False

        current_deg = get_sensor_value(sensors, config.SENSOR_ADXL)
        error       = current_deg - clamped_deg

        if abs(error) <= tolerance:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] Tilt target reached: {current_deg:.1f}° "
                  f"(target {clamped_deg:.1f}°).")
            return True

        # Positive error → currently tilted too far → retract to reduce angle
        # Negative error → not tilted enough        → extend to increase angle
        ser.write(cmd_retract if error > 0 else cmd_extend)
        time.sleep(0.05)


def retract_tilt(sensors: dict, ser, timeout: float = 30) -> bool:
    """
    Drive the tilt actuator (Motor 3) to config.MIN_ANGLE_DEG.

    Use this to return the tilt axis to its fully retracted (minimum angle)
    position, for example during shutdown or before re-calibration.

    Parameters
    ----------
    sensors : Dictionary of initialised sensor objects.
    ser     : Open serial.Serial object.
    timeout : Maximum movement time in seconds (default 30 s).

    Returns
    -------
    True if the minimum angle was reached, False on timeout.
    """
    if ser is None:
        raise ValueError("A serial port object is required for motor control.")

    cmd_retract = _get_motor_commands(config.SENSOR_ADXL)["retract"]

    print(f"[motor] Retracting tilt actuator to minimum angle "
          f"({config.MIN_ANGLE_DEG}°) …")

    start_time = time.monotonic()

    while time.monotonic() - start_time < timeout:
        current_deg = get_sensor_value(sensors, config.SENSOR_ADXL)

        if current_deg <= config.MIN_ANGLE_DEG:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] Tilt retracted to {current_deg:.1f}°.")
            return True

        ser.write(cmd_retract)
        time.sleep(0.1)

    ser.write(config.CMD_ALL_OFF)
    print(f"[motor] Timeout while retracting tilt actuator.")
    return False


# ---------------------------------------------------------------------------
# Emergency stop
# ---------------------------------------------------------------------------

def emergency_stop(ser) -> None:
    """Send an immediate stop command to all motors."""
    _send_all_off(ser, "[motor] EMERGENCY STOP — all motors disabled.")


def stop(ser) -> None:
    """Send a normal stop command to all motors.

    This intentionally sends the same hardware command as emergency_stop.
    The only difference in this module is logging/message semantics.
    """
    _send_all_off(ser, "[motor] Stop requested — all motors halted.")


def _send_all_off(ser, message: str) -> None:
    """Send the all-off command and emit a status message."""
    ser.write(config.CMD_ALL_OFF)
    print(message)
