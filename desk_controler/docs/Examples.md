# Usage Examples

Practical code examples for the Automated Desk Controller.

## Table of Contents

- [Basic Initialization and Reading](#example-1-basic-initialization-and-reading)
- [Calibration Workflow](#example-2-calibration-workflow)
- [Controlled Movement](#example-3-controlled-movement)
- [Continuous Monitoring](#example-4-continuous-monitoring)
- [Calibrated Readings](#example-5-with-calibrated-readings)
- [Tilt Angle Control](#example-6-tilt-angle-control)
- [MQTT Integration](#example-7-mqtt-integration)
- [Error Handling](#example-8-error-handling)
- [Common Patterns](#common-patterns-in-the-code)

---

### Example 1: Basic Initialization and Reading

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
    ser.write(config.CMD_ALL_OFF)
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

---

### Example 6: Tilt Angle Control

```python
from hardware.i2c_utils import init_i2c, init_mux
from hardware.sensors import init_adxl345, get_sensor_value
from hardware.serial_comm import init_serial
from motor_control import move_to_angle, retract_tilt
import config

# Initialize
i2c = init_i2c()
tca = init_mux(i2c)
sensors = {
    config.SENSOR_ADXL: init_adxl345(tca),
}
ser = init_serial()

# Read current tilt angle
angle = get_sensor_value(sensors, config.SENSOR_ADXL)
print(f"Current tilt: {angle:.1f}°")

# Move to 90° (perpendicular)
success = move_to_angle(sensors, target_deg=90.0, ser=ser)
if success:
    print("Tilt target reached!")
else:
    print("Tilt move timed out")

# Return to minimum angle (fully retracted tilt)
retract_tilt(sensors, ser)
```

---

### Example 7: MQTT Integration

```python
import paho.mqtt.client as mqtt
import json
import config
from motor_control import move_to_distance, emergency_stop

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(config.MQTT_TOPIC_COMMAND)
    else:
        print(f"Connection failed: rc={rc}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"Received command: {payload}")

    sensors = userdata["sensors"]
    ser = userdata["ser"]

    try:
        data = json.loads(payload)
        command = data.get("command")
        value = data.get("value")

        if command == "move_distance":
            success = move_to_distance(sensors, config.SENSOR_VL53_0, float(value), ser)
            status = "reached" if success else "timeout"
        elif command == "stop":
            emergency_stop(ser)
            status = "stopped"
        else:
            status = f"unknown command: {command}"

        client.publish(config.MQTT_TOPIC_STATUS, json.dumps({"status": status}))

    except Exception as e:
        print(f"Error processing command: {e}")
        emergency_stop(ser)

# Setup client
client = mqtt.Client()
client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.user_data_set({"sensors": sensors, "ser": ser})

client.connect(config.MQTT_BROKER, config.MQTT_PORT)
client.loop_forever()
```

**Example MQTT command payload:**
```json
{"command": "move_distance", "value": 150}
```

---

### Example 8: Error Handling

```python
from hardware.i2c_utils import init_i2c, init_mux
from hardware.sensors import init_vl53l0x
from hardware.serial_comm import init_serial
from motor_control import move_to_distance, emergency_stop
import config

sensors = {}
ser = None

try:
    # Initialize hardware
    i2c = init_i2c()
    tca = init_mux(i2c)
    sensors[config.SENSOR_VL53_0] = init_vl53l0x(
        tca, config.VL53_CHANNEL_1, "VL53L0X #1"
    )
    ser = init_serial()

    if ser is None:
        raise RuntimeError("Serial port failed to open")

    # Move with timeout protection
    success = move_to_distance(
        sensors, config.SENSOR_VL53_0, target_mm=150, ser=ser, timeout=20
    )
    if not success:
        print("WARNING: Movement timed out — position may not be reached")

except RuntimeError as e:
    print(f"Hardware error: {e}")

except Exception as e:
    print(f"Unexpected error: {e}")
    raise

finally:
    # Always attempt to stop motors, even after an error
    if ser is not None:
        emergency_stop(ser)
        ser.close()
```

---

## See Also

- [Key Concepts](Key_concepts.md) — Background on I2C, sensors, and closed-loop control
- [Calibration Guide](Calibration.md) — How to calibrate sensors before use
- [Troubleshooting Guide](Troubleshooting%20Guide.md) — Common issues and solutions
- [desk_controler/README.md](../README.md) — Full technical architecture and API reference

