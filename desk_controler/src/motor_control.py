"""
Motor control functions for actuator positioning using VL53L0X sensors.

All sensor names and motor commands are resolved through config constants —
no bare string literals or direct byte literals appear in this module.
"""

import time

import config
from hardware import get_sensor_value


def _get_motor_commands(sensor_name: str) -> dict:
    """
    Return the ``{"extend": ..., "retract": ...}`` command dict for *sensor_name*.

    Raises
    ------
    ValueError
        If *sensor_name* has no associated motor commands in config.
    """
    try:
        return config.SENSOR_MOTOR_COMMANDS[sensor_name]
    except KeyError:
        valid = list(config.SENSOR_MOTOR_COMMANDS.keys())
        raise ValueError(
            f"No motor commands defined for sensor '{sensor_name}'. "
            f"Valid sensors: {valid}"
        )


def move_to_distance(sensors: dict, sensor_name: str, target_mm: int,
                     ser, tolerance: int = 2, timeout: float = 30) -> bool:
    """
    Move an actuator until its paired sensor reads *target_mm*.

    Parameters
    ----------
    sensors:
        Dictionary of initialised sensor objects.
    sensor_name:
        One of the ``config.SENSOR_VL53_*`` constants.
    target_mm:
        Target distance in millimetres.
    ser:
        Open ``serial.Serial`` object used to send motor commands.
    tolerance:
        Acceptable distance error in millimetres (default 2 mm).
    timeout:
        Maximum movement duration in seconds (default 30 s).

    Returns
    -------
    bool
        ``True`` if the target was reached, ``False`` on timeout.
    """
    if ser is None:
        raise ValueError("A serial port object is required for motor control.")

    motor_cmds = _get_motor_commands(sensor_name)
    cmd_extend  = motor_cmds["extend"]
    cmd_retract = motor_cmds["retract"]
    
    clamped_mm = max(config.MIN_POSITION, min(config.MAX_POSITION, target_mm))

    if clamped_mm != target_mm:
        print(f"[motor] Position {target_mm} mm clamped to {clamped_mm} mm "
              f"(limits: {config.MIN_POSITION}–{config.MAX_POSITION} mm).")
    
    target_distance = target_distance - config.OFFSET[name]

    print(f"[motor] Moving '{sensor_name}' → {target_mm} mm  (±{tolerance} mm)")

    start_time = time.monotonic()

    while True:
        if time.monotonic() - start_time > timeout:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] Timeout after {timeout} s — motion aborted.")
            return False

        current_mm = get_sensor_value(sensors, sensor_name)
        error      = current_mm - target_mm

        if abs(error) <= tolerance:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] Target reached: {current_mm} mm (target {target_mm} mm).")
            return True

        # Positive error  → sensor reads too far → retract
        # Negative error  → sensor reads too close → extend
        ser.write(cmd_retract if error > 0 else cmd_extend)

        time.sleep(0.05)   # Avoid overwhelming the sensor



def retract_fully(sensors: dict, sensor_name: str,
                  ser, timeout: float = 30) -> bool:
    """
    Drive an actuator to the minimum safe position (``config.MIN_POSITION``).

    Parameters
    ----------
    sensors:
        Dictionary of initialised sensor objects.
    sensor_name:
        One of the ``config.SENSOR_VL53_*`` constants.
    ser:
        Open ``serial.Serial`` object.
    timeout:
        Maximum movement duration in seconds (default 30 s).

    Returns
    -------
    bool
        ``True`` if fully retracted, ``False`` on timeout.
    """
    if ser is None:
        raise ValueError("A serial port object is required for motor control.")

    motor_cmds  = _get_motor_commands(sensor_name)
    cmd_retract = motor_cmds["retract"]

    print(f"[motor] Retracting '{sensor_name}' to minimum position "
          f"({config.MIN_POSITION} mm) …")

    start_time = time.monotonic()

    while time.monotonic() - start_time < timeout:
        current_mm = get_sensor_value(sensors, sensor_name)

        if current_mm <= config.MIN_POSITION:
            ser.write(config.CMD_ALL_OFF)
            print(f"[motor] '{sensor_name}' retracted to {current_mm} mm.")
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
