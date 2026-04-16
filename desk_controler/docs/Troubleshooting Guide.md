# Troubleshooting Guide

Solutions to common hardware and software issues with the Automated Desk Controller.

## Table of Contents

- [I2C Issues](#i2c-issues)
- [Sensor Issues](#sensor-issues)
- [Motor / Actuator Issues](#motor--actuator-issues)
- [Calibration Issues](#calibration-issues)
- [Serial Port Issues](#serial-port-issues)
- [MQTT Issues](#mqtt-issues)
- [Software / Import Issues](#software--import-issues)
- [Diagnostic Commands](#diagnostic-commands)

---

## I2C Issues

### "I2C device not found"

**Cause:** Wiring issue, wrong address, or I2C not enabled.  
**Fix:**
- Check all SDA and SCL connections
- Run `i2cdetect -y 1` on the Raspberry Pi — you should see `0x70` (TCA9548A)
- Verify I2C is enabled: `sudo raspi-config` → Interface Options → I2C → Enable
- Reboot after enabling: `sudo reboot`

### `i2cdetect -y 1` shows no devices

**Cause:** I2C bus not enabled, wiring error, or damaged component.  
**Fix:**
- Confirm 3.3 V power is connected to the TCA9548A VCC pin
- Make sure SDA and SCL are not swapped
- Check for loose or broken jumper wires
- Add 4.7 kΩ pull-up resistors on SDA and SCL if the bus is long

### "Address 0xXX found on channel X, expected 0xXX"

**Cause:** Incorrect sensor connected to the wrong channel.  
**Fix:**
- Check sensor connections against the channel map:
  - Channel 0 → VL53L0X #1 (address `0x29`)
  - Channel 1 → VL53L0X #2 (address `0x29`)
  - Channel 2 → ADXL345 (address `0x53`)
- Re-run `i2cdetect -y 1` to confirm the TCA9548A address (`0x70`) is visible

---

## Sensor Issues

### "Sensors give wildly different readings"

**Cause:** One sensor is faulty, misaligned, or pointing at a different object.  
**Fix:**
- Hold a flat surface at a known distance in front of each sensor and compare readings
- Re-calibrate both sensors from the retracted position (see [Calibration Guide](Calibration.md))
- Replace the faulty sensor if readings remain inconsistent

### VL53L0X returns 8190 mm or 0 mm

**Cause:** Sensor timeout — no valid reflection received.  
**Fix:**
- Check the sensor is pointing at a surface within 2000 mm
- Verify 3.3 V power is stable
- Check for I2C bus errors: `dmesg | grep i2c`

### ADXL345 returns constant values or all zeros

**Cause:** Sensor not initialised correctly or I2C wiring issue on channel 2.  
**Fix:**
- Verify the ADXL345 is connected to **channel 2** of the TCA9548A
- Confirm the I2C address is `0x53` with `i2cdetect` after selecting channel 2
- Check 3.3 V and GND connections to the ADXL345

### Sensor timeout during initialisation

**Cause:** Slow I2C bus or bad connection causing reads to hang.  
**Fix:**
- Check I2C wiring length (keep under 30 cm where possible)
- Add 4.7 kΩ pull-up resistors to SDA and SCL
- Reduce I2C speed in `config.py` if your Pi supports it

---

## Motor / Actuator Issues

### "Motor moves but doesn't stop at target"

**Cause:** Closed-loop control is not receiving sensor feedback during movement.  
**Fix:**
- Verify the sensor updates while the actuator is moving (add print statements)
- Check that the correct sensor is mapped to the correct motor in `config.SENSOR_MOTOR_COMMANDS`
- Confirm the serial connection to the motor controller is stable

### Actuator moves in the wrong direction

**Cause:** Extend/retract command wiring or software mapping is inverted.  
**Fix:**
- Swap the `extend` and `retract` commands for the affected motor in `config.SENSOR_MOTOR_COMMANDS`
- Or swap the physical wiring to the motor controller

### Motor doesn't respond to commands

**Cause:** Serial port not open, wrong port, or motor controller not powered.  
**Fix:**
- Verify the serial port path: `ls /dev/serial*` — expect `/dev/serial0`
- Check motor controller power supply
- Confirm the user is in the `dialout` group: `sudo usermod -a -G dialout $USER` then reboot

### Actuator overshoots target position

**Cause:** Motor inertia — the actuator continues moving after the stop command.  
**Fix:**
- Increase the `tolerance` parameter in `move_to_distance()` (default is ±2 mm)
- Reduce the movement step delay if the control loop is too slow

---

## Calibration Issues

### `RuntimeError: No calibration data available`

**Cause:** Calibration has not been run; `config.OFFSET` is empty or missing.  
**Fix:**
- Run the calibration routine from `desk_controler/src/`:
  ```bash
  cd desk_controler/src
  python3 -c "from calibration import calibrate_vl53_sensors; ..."
  ```
- See [Calibration Guide](Calibration.md) for the full procedure

### Corrected readings are not near 0 mm at the retracted position

**Cause:** Calibration was run with the actuators not fully retracted.  
**Fix:**
- Manually retract all actuators to the physical stop
- Re-run calibration

### `config.py` not updated after calibration

**Cause:** Script is not running from the `src/` directory.  
**Fix:**
- Always `cd desk_controler/src` before running calibration

---

## Serial Port Issues

### `SerialException: [Errno 13] Permission denied: '/dev/serial0'`

**Cause:** User does not have permission to access the serial port.  
**Fix:**
```bash
sudo usermod -a -G dialout $USER
sudo reboot
```

### `SerialException: [Errno 2] No such file or directory: '/dev/serial0'`

**Cause:** Serial port not enabled on the Raspberry Pi.  
**Fix:**
```bash
sudo raspi-config
# Navigate to: Interface Options → Serial Port
#   → Disable login shell over serial → Yes
#   → Enable serial port hardware → Yes
sudo reboot
```

### Commands sent but actuator doesn't move

**Cause:** Motor controller not receiving commands, or wrong baud rate.  
**Fix:**
- Verify baud rate is **2400** (set in `config.SERIAL_BAUDRATE`)
- Check TX/RX wiring: Pi TX → Controller RX, Pi RX → Controller TX
- Confirm GND is shared between the Pi and motor controller

---

## MQTT Issues

### Desk controller not responding to MQTT commands

**Cause:** Broker address, credentials, or topic mismatch.  
**Fix:**
- Verify broker settings in `config.py`:
  ```python
  MQTT_BROKER = "192.168.1.138"
  MQTT_PORT = 1883
  MQTT_USERNAME = "eceMos"
  ```
- Confirm the broker is running: `mosquitto_pub -h <broker> -t test -m hello`
- Check that the command topic matches: `MQTT_TOPIC_COMMAND = "home/desk/command"`

### MQTT connection refused

**Cause:** Broker not running or firewall blocking port 1883.  
**Fix:**
- Start the broker: `sudo systemctl start mosquitto`
- Check the firewall: `sudo ufw allow 1883`

---

## Software / Import Issues

### `ModuleNotFoundError: No module named 'adafruit_vl53l0x'`

**Cause:** Python dependencies not installed.  
**Fix:**
```bash
cd desk_controler/src
pip install -r requirements.txt
```

### `ModuleNotFoundError: No module named 'board'`

**Cause:** Running on a non-Raspberry Pi machine or `adafruit-blinka` not installed.  
**Fix:**
- These libraries require real I2C hardware; run on a Raspberry Pi
- For unit testing without hardware, use the mock-based test suite:
  ```bash
  cd desk_controler/tests
  python -m pytest -q
  ```

---

## Diagnostic Commands

| Task | Command |
|------|---------|
| Scan I2C bus | `i2cdetect -y 1` |
| Check serial ports | `ls /dev/serial*` |
| Check I2C kernel messages | `dmesg \| grep i2c` |
| Verify Python version | `python3 --version` |
| Check installed packages | `pip list \| grep -E 'adafruit\|pyserial'` |
| View calibration offsets | `grep "^OFFSET" desk_controler/src/config.py` |
| Run all tests | `cd desk_controler/tests && python -m pytest -q` |

---

## See Also

- [Calibration Guide](Calibration.md) — Detailed calibration procedures
- [Quick Start Guide](quickstart_guide.md) — Initial setup walkthrough
- [Key Concepts](Key_concepts.md) — Background on I2C, sensors, and control loops
- [desk_controler/README.md](../README.md) — Full technical architecture

