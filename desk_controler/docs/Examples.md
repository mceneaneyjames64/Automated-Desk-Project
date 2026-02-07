# Usage Examples

### Example 1: Basic Initialization and Reading

```python
# Initialize everything
sensors = init_all_hardware()
ser = init_serial()

# Read a distance sensor
distance = get_sensor_value(sensors, 'vl53l0x_0')
print(f"Current distance: {distance}mm")

# Read accelerometer
accel = get_sensor_value(sensors, 'adxl345')
print(f"Acceleration: X={accel['x']}, Y={accel['y']}, Z={accel['z']}")
```

### Example 2: Calibration Workflow

```python
# Try to load existing calibration
calibration_data = load_calibration()

if calibration_data is None:
    # No calibration found - create new one
    print("Running calibration...")
    calibration_data = calibrate_vl53_sensors(sensors)
    print("Calibration complete!")
else:
    print("Loaded existing calibration")

# Show calibration info
print_calibration_info(calibration_data)
```

### Example 3: Controlled Movement

```python
# Move to absolute position
move_station_distance(sensors, 'vl53l0x_0', 150, ser)
# → Motor moves until sensor reads 150mm

# Move relative to home
move_station_distance_calibrated(sensors, calibration_data, 'vl53l0x_0', 50, ser)
# → Extends 50mm from calibrated baseline

# Return home
move_to_retracted(sensors, 'vl53l0x_0', ser)
# → Retracts to minimum safe position

# Emergency stop
emergency_stop(ser)
# → Immediate halt
```

### Example 4: Continuous Monitoring

```python
import time

while True:
    # Read both distance sensors
    dist1 = get_sensor_value(sensors, 'vl53l0x_0')
    dist2 = get_sensor_value(sensors, 'vl53l0x_1')
    
    # Read accelerometer
    accel = get_sensor_value(sensors, 'adxl345')
    
    # Print status
    print(f"Sensor 1: {dist1}mm | Sensor 2: {dist2}mm")
    print(f"Accel: X={accel['x']:.2f}g Y={accel['y']:.2f}g Z={accel['z']:.2f}g")
    
    # Check for problems
    if abs(dist1 - dist2) > 10:
        print("WARNING: Sensors disagree!")
        emergency_stop(ser)
    
    time.sleep(1)  # Wait 1 second
```

### Example 5: With Calibrated Readings

```python
# Get raw and calibrated readings
reading = get_calibrated_reading(sensors, 'vl53l0x_0', calibration_data)

print(f"Raw reading: {reading['raw_mm']}mm")
print(f"Baseline: {reading['baseline_mm']}mm")
print(f"Offset from baseline: {reading['offset_mm']}mm")

# Example output:
# Raw reading: 150mm
# Baseline: 100mm
# Offset from baseline: 50mm
# → You're 50mm extended from home position
```
---

## Common Patterns in the Code

### Pattern 1: Try-Except-Finally for Hardware

```python
try:
    # Initialize hardware
    sensors = init_all_hardware()
    ser = init_serial()
    
    # Do work...
    
except Exception as e:
    print(f"Error: {e}")
    return 1
    
finally:
    # Always turn off motor (safety!)
    ser.write(config.OFF)
```

**Why**: Hardware can fail unpredictably. Always clean up!

### Pattern 2: Sensor Reading with Error Handling

```python
try:
    value = get_sensor_value(sensors, 'vl53l0x_0')
except Exception:
    # Sensor failed - use safe default or stop
    emergency_stop(ser)
    raise
```

### Pattern 3: Closed-Loop Control

```python
while True:
    current = get_sensor_value(sensors, 'vl53l0x_0')
    error = target - current
    
    if abs(error) < tolerance:
        break  # Close enough!
    
    # Send movement command proportional to error
    move_command = calculate_command(error)
    ser.write(move_command)
```
