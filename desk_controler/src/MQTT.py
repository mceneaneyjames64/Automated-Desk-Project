def handle_motor_move(client: mqtt.Client, motor_id: int, direction: str):
    """
    Handle motor movement command.
    
    Parameters
    ----------
    client : mqtt.Client
        MQTT client
    motor_id : int
        Motor ID (1-3)
    direction : str
        "up", "down", or numeric position value
    """
    try:
        # Correct sensor mapping from config.py
        sensor_map = {
            1: config.SENSOR_ADXL,      # Motor 1 → ADXL345
            2: config.SENSOR_VL53_0,    # Motor 2 → VL53L0X_0
            3: config.SENSOR_VL53_1     # Motor 3 → VL53L0X_1
        }
        sensor_name = sensor_map.get(motor_id)
        
        if direction.lower() == "up":
            print(f"  → Motor {motor_id}: EXTEND")
            if sensor_name and calibration_sensors:
                move_to_distance(
                    calibration_sensors,
                    sensor_name,
                    config.MAX_POSITION,
                    _require_motor_serial_port("motor move up")
                )
                client.publish(TOPIC_STATUS, f"M{motor_id} extended")
            else:
                raise RuntimeError(f"Sensor or calibration not available for M{motor_id}")
        
        elif direction.lower() == "down":
            print(f"  → Motor {motor_id}: RETRACT")
            if sensor_name and calibration_sensors:
                retract_fully(
                    calibration_sensors,
                    sensor_name,
                    _require_motor_serial_port("motor move down")
                )
                client.publish(TOPIC_STATUS, f"M{motor_id} retracted")
            else:
                raise RuntimeError(f"Sensor or calibration not available for M{motor_id}")
        
        elif direction.lower() == "stop":
            print(f"  → Motor {motor_id}: STOP")
            stop(_require_motor_serial_port("motor stop"))
            client.publish(TOPIC_STATUS, f"M{motor_id} stopped")
        
        else:
            # Try to parse as position value
            try:
                target_mm = float(direction)
                print(f"  → Motor {motor_id}: MOVE TO {target_mm} mm")
                if sensor_name and calibration_sensors:
                    move_to_distance(
                        calibration_sensors,
                        sensor_name,
                        target_mm,
                        _require_motor_serial_port("motor move to position")
                    )
                    client.publish(TOPIC_STATUS, f"M{motor_id} moved to {target_mm}mm")
                else:
                    raise RuntimeError(f"Sensor or calibration not available for M{motor_id}")
            except ValueError:
                print(f"✗ Invalid direction format: {direction}")
                client.publish(TOPIC_STATUS, f"Invalid direction: {direction}")
    
    except Exception as e:
        print(f"✗ Error in handle_motor_move: {e}")
        client.publish(TOPIC_STATUS, f"Error: {e}")
