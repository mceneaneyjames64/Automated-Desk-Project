"""
Motor control functions for actuator positioning using VL53L0X sensors.

All sensor names and motor commands are resolved through config constants —
no bare string literals or direct byte literals appear in this module.

Offset correction
-----------------
config.OFFSET stores a per-sensor software offset (float, mm) produced by
calibration.  The sensor systematically over- or under-reads by this amount,
so every raw reading must be corrected before comparing it against a target:

    corrected_mm = raw_mm + offset

All movement loops call _read_corrected() instead of get_sensor_value()
directly, so offset correction is applied in exactly one place.
"""

import time

import config
from hardware import get_sensor_value


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_motor_commands(sensor_name: str) -> dict:
    """Return the extend/retract command dict for sensor_name."""
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
    Return the offset-corrected distance for sensor_name.

    Applies config.OFFSET[sensor_name] to the raw reading.  If no offset is
    present for this sensor (e.g. calibration has not been run yet) the raw
    reading is returned unchanged and a warning is printed once.
    """
    raw = get_sensor_value(sensors, sensor_name)
    offset = getattr(config, "OFFSET", {}).get(sensor_name)
    if offset is None:
        print(f"[motor] Warning: no calibration offset for '{sensor_name}' — "
              f"using raw reading.")
        return raw
    return raw + offset


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def move_to_distance(sensors: dict, sensor_name: str, target_mm: float,
                     ser, tolerance: int = 2, timeout: float = 30) -> bool:
    """
    Move an actuator until its corrected sensor reading reaches target_mm.

    Parameters
    ----------
    sensors     : Dictionary of initialised sensor objects.
    sensor_name : One of the config.SENSOR_VL53_* constants.
    target_mm   : Desired true distance in millimetres.
    ser         : Open serial.Serial object.
    tolerance   : Acceptable error in mm (default 2 mm).
    timeout     : Maximum movement time in seconds (default 30 s).

    Returns
    -------
    True if target reached, False on timeout.
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

        # Positive error  → sensor reads too far → retract
        # Negative error  → sensor reads too close → extend
        ser.write(cmd_retract if error > 0 else cmd_extend)
        time.sleep(0.05)


def retract_fully(sensors: dict, sensor_name: str,
                  ser, timeout: float = 30) -> bool:
    """
    Drive an actuator to config.MIN_POSITION using corrected sensor readings.

    Parameters
    ----------
    sensors     : Dictionary of initialised sensor objects.
    sensor_name : One of the config.SENSOR_VL53_* constants.
    ser         : Open serial.Serial object.
    timeout     : Maximum movement time in seconds (default 30 s).

    Returns
    -------
    True if fully retracted, False on timeout.
    """
    if ser is None:
        raise ValueError("A serial port object is required for motor control.")

    motor_cmds  = _get_motor_commands(sensor_name)
    cmd_retract = motor_cmds["retract"]

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


def emergency_stop(ser) -> None:
    """Send an immediate stop command to all motors."""
    ser.write(config.CMD_ALL_OFF)
    print("[motor] EMERGENCY STOP — all motors disabled.")


def stop(ser) -> None:
    """Send a normal stop command to all motors."""
    ser.write(config.CMD_ALL_OFF)
    print("[motor] Stop requested — all motors halted.")
