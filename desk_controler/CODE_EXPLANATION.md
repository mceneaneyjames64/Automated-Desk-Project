# Hardware Control System - Code Explanation

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Hardware Components](#hardware-components)
3. [Code Flow](#code-flow)
4. [Detailed Function Explanations](#detailed-function-explanations)
5. [Key Concepts](#key-concepts)
6. [Usage Examples](#usage-examples)

---

## 🎯 System Overview

This is a **hardware control system** that manages a motorized positioning station with multiple sensors. Think of it like a robotic arm or linear actuator that can:

- **Move to precise positions** using motor control
- **Measure distance** using laser sensors (VL53L0X)
- **Detect motion/vibration** using an accelerometer (ADXL345)
- **Calibrate itself** to know its baseline/home position
- **Communicate** with motor controllers via serial port

### Real-World Analogy
Imagine a 3D printer's print head that needs to:
- Know exactly where it is (distance sensors)
- Move to specific positions (motor control)
- Know when it's "home" (calibration)
- Detect if something bumps it (accelerometer)

---

## 🔧 Hardware Components

### 1. **I2C Bus & Multiplexer (TCA9548A)**
```
┌─────────────────┐
│  Raspberry Pi   │
│   (or similar)  │
└────────┬────────┘
         │ I2C Bus (2 wires: SDA, SCL)
         │
    ┌────▼────┐
    │   MUX   │ ← Multiplexer (TCA9548A)
    │ TCA9548A│   Allows multiple devices on same I2C address
    └─┬─┬─┬─┬─┘
      │ │ │ │
      Ch0,1,2,3... (8 channels)
```

**Why a multiplexer?**
- VL53L0X sensors all use the same I2C address (0x29)
- Can't have two devices with same address on same bus
- Multiplexer creates 8 "virtual" I2C buses
- You can put one sensor on each channel

### 2. **VL53L0X Distance Sensors (2x)**
- **What**: Laser time-of-flight distance sensors
- **Range**: ~30mm to 2000mm
- **Accuracy**: ±3% 
- **How it works**: Sends laser pulse, measures time for reflection
- **Use case**: Tells you exactly how far extended the motor is

```
Sensor → [═══════] ← Target Object
         \       /
          \ 150mm/
           \   /
            \_/
```

### 3. **ADXL345 Accelerometer**
- **What**: 3-axis motion sensor (X, Y, Z)
- **Use case**: Detects if system is moving, tilted, or vibrating
- **Output**: Acceleration in g's (gravity units)
  - Stationary: (0, 0, 9.8) = gravity pulling down
  - Moving: Changes in X, Y, Z values

### 4. **Motor Controller (Serial Communication)**
- **What**: Controls a stepper or DC motor
- **Interface**: Serial port (UART) - sends byte commands
- **Commands**: Move, Stop, Set Position, etc.

---

## 🔄 Code Flow

### Main Program Execution Flow

```
START
  │
  ├─→ Initialize I2C Bus
  │
  ├─→ Initialize Multiplexer (TCA9548A)
  │
  ├─→ Initialize VL53L0X Sensors (on channels 1 & 2)
  │
  ├─→ Initialize ADXL345 (on another channel)
  │
  ├─→ Initialize Serial Port (for motor control)
  │
  ├─→ Load or Create Calibration Data
  │    │
  │    ├─→ If no calibration file exists:
  │    │    └─→ Run calibration (measure baseline positions)
  │    │
  │    └─→ If calibration exists:
  │         └─→ Load from file
  │
  ├─→ Perform Motor Movements
  │    │
  │    ├─→ Move to absolute position (100mm)
  │    ├─→ Move relative to baseline (+50mm from home)
  │    ├─→ Retract to home position
  │    └─→ Emergency stop
  │
  └─→ Continuous Monitoring Loop
       │
       └─→ Read sensors every 10 seconds
           ├─→ VL53L0X #1 distance
           ├─→ VL53L0X #2 distance
           └─→ ADXL345 acceleration
```

---

## 📖 Detailed Function Explanations

### 1. `init_all_hardware()`

**Purpose**: Initialize all hardware components in the correct order

```python
def init_all_hardware():
    sensors = {}
    
    # Step 1: Initialize I2C bus
    i2c = init_i2c()  # Creates I2C connection
    
    # Step 2: Initialize multiplexer
    tca = init_mux(i2c)  # Sets up the 8-channel switch
    sensors["mux"] = tca
    
    # Step 3: Initialize distance sensors on different channels
    sensors["vl53l0x_0"] = init_vl53l0x(tca, config.VL53_CHANNEL_1, "VL53L0X #1")
    sensors["vl53l0x_1"] = init_vl53l0x(tca, config.VL53_CHANNEL_2, "VL53L0X #2")
    
    # Step 4: Initialize accelerometer
    sensors["adxl345"] = init_adxl345(tca)
    
    return sensors
```

**Why this order matters:**
1. Must create I2C bus first (it's the communication highway)
2. Must initialize multiplexer second (it controls access to channels)
3. Then initialize individual sensors on their assigned channels

---

### 2. `calibrate_vl53_sensors(sensors)`

**Purpose**: Establish a "home" or "baseline" position for the system

**How it works:**
```python
# Conceptual flow:
1. System is at unknown position
2. Take 10 distance readings from sensor
3. Average them to get baseline
   Example: [100, 101, 99, 100, 100, 101, 99, 100, 101, 100]
   Average: 100.1mm ← This is your "home position"
4. Save this to a file (calibration.json)
```

**Why calibration is needed:**
- Sensors measure absolute distance to nearest object
- But you want to know position **relative to a starting point**
- Calibration says "THIS is position zero"
- All future movements are relative to this

**Example:**
```
Calibration baseline: 100mm
Current reading: 150mm
→ You've moved 50mm from home position
```

---

### 3. `move_station_distance(sensors, sensor_name, target_mm, ser)`

**Purpose**: Move motor to an **absolute** distance reading

```python
# Example call:
move_station_distance(sensors, 'vl53l0x_0', 150, ser)

# What happens:
1. Current position: Read sensor → 100mm
2. Target position: 150mm
3. Calculate: Need to move +50mm
4. Send motor command: "Move forward 50mm"
5. Monitor sensor during movement
6. Stop when sensor reads 150mm
```

**Closed-Loop Control:**
```
     ┌─────────────────────────────┐
     │                             │
     ▼                             │
[Read Sensor] → [Calculate Error] → [Send Motor Command]
                       │
                       └─→ Error = Target - Current
```

---

### 4. `move_station_distance_calibrated(sensors, calibration_data, sensor_name, relative_mm, ser)`

**Purpose**: Move **relative to the calibrated baseline**

```python
# Example:
# Baseline (from calibration): 100mm
# Current position: 100mm (at home)
# Command: Move +50mm relative

move_station_distance_calibrated(sensors, calibration_data, 'vl53l0x_0', 50, ser)

# What happens:
1. Load baseline: 100mm
2. Calculate target: 100mm + 50mm = 150mm
3. Move to absolute position 150mm
4. You're now 50mm extended from home
```

**Why two movement functions?**
- `move_station_distance()` → "Go to 150mm" (absolute)
- `move_station_distance_calibrated()` → "Extend 50mm from home" (relative)

---

### 5. `move_to_retracted(sensors, sensor_name, ser)`

**Purpose**: Return to the fully retracted (home) position

```python
# Usually retracts to the smallest safe distance
# Like a 3D printer returning print head to home corner

move_to_retracted(sensors, 'vl53l0x_0', ser)
# → Moves until sensor reads minimum safe distance
```

---

### 6. `emergency_stop(ser)`

**Purpose**: Immediately halt all motor movement

```python
emergency_stop(ser)
# Sends stop command to motor controller
# Critical for safety - must work instantly!
```

---

### 7. `get_sensor_value(sensors, sensor_name)`

**Purpose**: Read current value from a specific sensor

```python
# For distance sensor:
distance = get_sensor_value(sensors, 'vl53l0x_0')
print(distance)  # → 150 (mm)

# For accelerometer:
accel = get_sensor_value(sensors, 'adxl345')
print(accel)  # → {'x': 0.1, 'y': 0.2, 'z': 9.8}
```

---

## 🔑 Key Concepts

### 1. **I2C Communication**

```
┌──────────┐           ┌──────────┐
│ Computer │ ←──I2C──→ │  Sensor  │
└──────────┘           └──────────┘
     │
     └─ SDA (Data line)
     └─ SCL (Clock line)
```

- **SDA**: Bidirectional data
- **SCL**: Clock signal (timing)
- **Address**: Each device has a unique ID (e.g., 0x29, 0x53)
- Computer sends: "Hey device 0x29, give me a reading"

### 2. **Multiplexer Channels**

```
Without MUX:                    With MUX:
┌─────────┐                    ┌─────────┐
│ Device  │ 0x29               │ Device  │ 0x29
├─────────┤                    ├─────────┤
│ Device  │ 0x29 ← CONFLICT!   │ MUX Ch0 │ ─┐
└─────────┘                    ├─────────┤  │
                               │ Device  │ 0x29
                               ├─────────┤  │
                               │ MUX Ch1 │ ─┘
                               └─────────┘
```

The MUX acts like a railroad switch:
- Turn to Channel 0 → Talk to Sensor #1
- Turn to Channel 1 → Talk to Sensor #2

### 3. **Calibration Data Structure**

```json
{
  "vl53l0x_0": {
    "baseline_mm": 100.5,
    "offset": 0,
    "timestamp": 1638360000,
    "samples": 10
  },
  "vl53l0x_1": {
    "baseline_mm": 105.2,
    "offset": 0,
    "timestamp": 1638360000,
    "samples": 10
  }
}
```

**Fields:**
- `baseline_mm`: The "home" position distance
- `offset`: Additional correction factor
- `timestamp`: When calibration was done
- `samples`: How many readings were averaged

### 4. **Serial Communication**

```python
# Open serial port
ser = serial.Serial('/dev/ttyUSB0', 9600)

# Send command (bytes)
ser.write(b'\x01\x02\x03')  # Move command
ser.write(config.OFF)        # Stop command
```

**Common Serial Commands** (example):
- `b'\x01'` → Move forward
- `b'\x02'` → Move backward  
- `b'\x00'` → Stop
- `b'\x03\x64'` → Move to position 100

---

## 💡 Usage Examples

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

## 🎓 Common Patterns in the Code

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

---

## 🚨 Safety Considerations

### 1. **Always Have an Emergency Stop**
```python
emergency_stop(ser)  # Must work instantly
```

### 2. **Validate Sensor Readings**
```python
if distance < MIN_SAFE or distance > MAX_SAFE:
    emergency_stop(ser)
    raise ValueError("Sensor reading out of safe range")
```

### 3. **Timeout on Movements**
```python
start_time = time.time()
while not at_target():
    if time.time() - start_time > TIMEOUT:
        emergency_stop(ser)
        raise TimeoutError("Movement took too long")
```

### 4. **Cleanup in Finally Block**
```python
try:
    # Risky operations
    move_motor()
finally:
    # Always execute, even if error
    ser.write(config.OFF)
```

---

## 🔧 Troubleshooting Guide

### Problem: "I2C device not found"
**Cause**: Wiring issue or wrong address
**Fix**: 
- Check SDA/SCL connections
- Run `i2cdetect -y 1` (on Raspberry Pi)
- Verify device address in config

### Problem: "Sensors give wildly different readings"
**Cause**: One sensor is faulty or misaligned
**Fix**:
- Check sensor #2 isn't reading a different object
- Recalibrate both sensors
- Replace faulty sensor

### Problem: "Motor moves but doesn't stop at target"
**Cause**: Closed-loop control not working
**Fix**:
- Verify sensor updates during movement
- Check serial communication
- Add debug prints to see current position

### Problem: "Calibration file not found"
**Cause**: First run, no calibration saved
**Fix**: 
- Run calibration: `calibrate_vl53_sensors(sensors)`
- It will create calibration.json automatically

---

## 📚 Summary

This system is a **feedback-controlled positioning system**:

1. **Sensors** tell you where you are (VL53L0X) and if you're moving (ADXL345)
2. **Motor** moves the system to desired positions
3. **Calibration** establishes a reference point (home position)
4. **Control loop** continuously checks position and adjusts motor
5. **Safety features** prevent damage (emergency stop, range limits)

**Key Workflow:**
```
Initialize → Calibrate → Move → Monitor → Cleanup
```

**Think of it as:** A smart robotic positioner that knows where it is and can move to precise locations while monitoring for problems.

---

## 🎯 Next Steps

To understand the code better:
1. Read through `main.py` following this guide
2. Look at `hardware.py` to see how sensors are initialized
3. Study `motor_control.py` to understand movement logic
4. Check `calibration.py` to see how baseline is established
5. Run the code with print statements to see data flow

Good luck! 🚀
