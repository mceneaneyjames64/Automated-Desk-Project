"""
Motor control functions for actuator positioning using VL53L0X sensors
"""
import time
from hardware import get_sensor_value
import config


def move_station_distance(sensors, name, target_distance, ser=None, tolerance=2, timeout=30):
    """
    Move actuator to specific distance reading
    
    Args:
        sensors (dict): Dictionary of sensor objects
        name (str): Sensor name ('vl53l0x_0' or 'vl53l0x_1')
        target_distance (int): Target distance in mm
        ser: Serial port object for motor control (optional if just reading)
        tolerance (int): Acceptable distance tolerance in mm (default: 2mm)
        timeout (float): Maximum time to attempt movement in seconds
        
    Returns:
        bool: True if target reached, False if timeout
    """
    
    # Check if serial port provided
    if ser is None:
        raise ValueError("Serial port object (ser) is required for motor control")
    
    # Validate sensor name
    if name not in ['vl53l0x_0', 'vl53l0x_1']:
        raise ValueError(f"Invalid sensor name: {name}. Must be 'vl53l0x_0' or 'vl53l0x_1'")
    
    # Select motor commands based on sensor
    if name == 'vl53l0x_0':
        motor_in = config.M1_IN
        motor_out = config.M1_OUT
    else:  # vl53l0x_1
        motor_in = config.M2_IN
        motor_out = config.M2_OUT
    
    print(f"Moving {name} to {target_distance}mm (tolerance: ±{tolerance}mm)")
    
    start_time = time.monotonic()
    
    while True:
        # Check timeout
        if time.monotonic() - start_time > timeout:
            ser.write(config.OFF)
            print(f"Timeout reached after {timeout}s")
            return False
        
        # Get current distance
        current_distance = get_sensor_value(sensors, name)
        error = current_distance - target_distance
        
        # Check if within tolerance
        if abs(error) <= tolerance:
            ser.write(config.OFF)
            print(f"Target reached: {current_distance}mm (target: {target_distance}mm)")
            return True
        
        # Move based on error
        if error > tolerance:
            # Current distance > target, need to retract (move IN)
            ser.write(motor_in)
        elif error < -tolerance:
            # Current distance < target, need to extend (move OUT)
            ser.write(motor_out)
        
        time.sleep(0.05)  # Small delay to avoid overwhelming the sensor


def move_station_distance_calibrated(sensors, calibration_data, name, 
                                     target_offset, ser=None, tolerance=2, timeout=30):
    """
    Move actuator to specific offset from calibrated baseline
    
    Args:
        sensors (dict): Dictionary of sensor objects
        calibration_data (dict): Calibration data with baselines
        name (str): Sensor name ('vl53l0x_0' or 'vl53l0x_1')
        target_offset (int): Target offset from baseline in mm (positive = extended)
        ser: Serial port object for motor control (optional keyword argument)
        tolerance (int): Acceptable distance tolerance in mm
        timeout (float): Maximum time to attempt movement in seconds
        
    Returns:
        bool: True if target reached, False if timeout
    """
    if calibration_data is None or name not in calibration_data:
        raise RuntimeError(f"No calibration data for {name}")
    
    baseline = calibration_data[name]['baseline_mm']
    target_distance = baseline + target_offset
    
    print(f"Moving {name} to offset {target_offset}mm (absolute: {target_distance}mm)")
    
    return move_station_distance(sensors, name, target_distance, ser, tolerance, timeout)


def move_to_retracted(sensors, name, ser=None, timeout=30):
    """
    Move actuator to fully retracted position (MIN_POSITION)
    
    Args:
        sensors (dict): Dictionary of sensor objects
        name (str): Sensor name
        ser: Serial port object (optional keyword argument)
        timeout (float): Maximum time in seconds
        
    Returns:
        bool: True if successful
    """
    if ser is None:
        raise ValueError("Serial port object (ser) is required for motor control")
    
    print(f"Retracting {name} to minimum position...")
    
    # Select motor based on sensor
    motor_in = config.M1_IN if name == 'vl53l0x_0' else config.M2_IN
    
    start_time = time.monotonic()
    
    while time.monotonic() - start_time < timeout:
        current = get_sensor_value(sensors, name)
        
        # Check if we've reached minimum (distance stops decreasing)
        if current <= config.MIN_POSITION:
            ser.write(config.OFF)
            print(f"{name} retracted to {current}mm")
            return True
        
        ser.write(motor_in)
        time.sleep(0.1)
    
    ser.write(config.OFF)
    print(f"Timeout while retracting {name}")
    return False


def move_to_position_limits(sensors, name, position, ser=None, timeout=30):
    """
    Move actuator with safety limits enforced
    
    Args:
        sensors (dict): Dictionary of sensor objects
        name (str): Sensor name
        position (int): Target position in mm
        ser: Serial port object (optional keyword argument)
        timeout (float): Maximum time in seconds
        
    Returns:
        bool: True if target reached
    """
    # Enforce limits
    if position < config.MIN_POSITION:
        print(f"Warning: Position {position} below MIN_POSITION ({config.MIN_POSITION}), clamping")
        position = config.MIN_POSITION
    elif position > config.MAX_POSITION:
        print(f"Warning: Position {position} above MAX_POSITION ({config.MAX_POSITION}), clamping")
        position = config.MAX_POSITION
    
    return move_station_distance(sensors, name, position, ser, timeout=timeout)


def emergency_stop(ser):
    """Send emergency stop command to all motors"""
    ser.write(config.OFF)
    print("EMERGENCY STOP - All motors disabled")
