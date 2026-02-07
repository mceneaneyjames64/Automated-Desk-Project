## Troubleshooting Guide

### Problem: "I2C device not found"
**Cause**: Wiring issue or wrong address
**Fix**: 
- Check sensor connections
- Run `i2cdetect -y 1` (on Raspberry Pi)
- Verify device address in config

### Problem: "Address 0xXX found on channel X expected 0xXX"
**Cause**: Incorrect sensor on specified channel 
**Fix**: 
- Check sensor connections
- Run `i2cdetect -y 1` (on Raspberry Pi)
- Verify correct sensor is installed in specified channel

### Problem: "Sensors give wildly different readings"
**Cause**: One sensor is faulty or misaligned
**Fix**:
- Check sensor isn't reading against different object of known distance
- Re-calibrate both sensors
- Replace faulty sensor

### Problem: "Motor moves but doesn't stop at target"
**Cause**: Closed-loop control not working
**Fix**:
- Verify sensor updates during movement
- Check serial communication

### Problem: "Calibration file not found"
**Cause**: First run, no calibration saved
**Fix**: 
- Run calibration: `calibrate_vl53_sensors(sensors)`
- It will create calibration.json automatically

> Written with [StackEdit](https://stackedit.io/).
