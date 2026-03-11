# Quick Start Guide

Get your desk controller up and running in 15 minutes.

## What You'll Need:

### Hardware
- Raspberry Pi (3/4/5 or Zero 2 W)
- TCA9548A I2C Multiplexer
- 2x VL53L0X Time-of-Flight Distance Sensors
- 1x ADXL345 Accelerometer
- Serial motor controller
- Jumper wires
- Power supply (5V for Pi, check motor controller requirements)

### Software
- Raspberry Pi OS (Raspbian)
- Python 3.7 or newer
- Internet connection (for installation)

---

## Step 1: Hardware Setup (5 minutes)

### Wiring Connections

**Connect TCA9548A to Raspberry Pi:**
```
Raspberry Pi          TCA9548A Multiplexer
Pin 3 (GPIO2/SDA) ──→ SDA
Pin 5 (GPIO3/SCL) ──→ SCL
Pin 1 (3.3V)      ──→ VCC
Pin 6 (GND)       ──→ GND
```

**Connect Sensors to TCA9548A:**
```
TCA9548A Channel 0 ──→ VL53L0X #1 (SDA, SCL, VCC, GND)
TCA9548A Channel 1 ──→ VL53L0X #2 (SDA, SCL, VCC, GND)
TCA9548A Channel 2 ──→ ADXL345 (SDA, SCL, VCC, GND)
```

**Connect Motor Controller:**
```
Raspberry Pi          Motor Controller
Pin 8 (GPIO14/TX) ──→ RX
Pin 10 (GPIO15/RX)──→ TX
Pin 6 (GND)       ──→ GND
```

### Quick Wiring Reference
```
 ┌─────────────────────┐
 │   Raspberry Pi      │
 │  Pin 3 ──────┐      │
 │  Pin 5 ──────┼───┐  │
 │  3.3V  ──────┼───┼─┐│
 │  GND   ──────┼───┼─┼┤
 └──────────────┼───┼─┼┘
                │   │ │
         ┌──────▼───▼─▼────┐
         │    TCA9548A     │
         │    I2C Mux      │
         └─┬───┬───┬───────┘
   Ch0 ───┘   │   └─── Ch2
              │
             Ch1
              │
    ┌─────────┼──────────┐
    │         │          │
┌───▼───┐ ┌──▼────┐ ┌───▼────┐
│VL53L0X│ │VL53L0X│ │ADXL345 │
│  #1   │ │  #2   │ │ Accel  │
└───────┘ └───────┘ └────────┘
```

---

## Step 2: Raspberry Pi Setup (3 minutes)

### Enable I2C
```bash
# Open Raspberry Pi configuration
sudo raspi-config

# Navigate to:
# 3. Interface Options
#   → I5 I2C
#     → Yes (Enable)
#       → OK
#         → Finish
```

### Verify I2C is Working
```bash
# Check I2C devices exist
ls /dev/i2c-*
# Should show: /dev/i2c-1

# Scan for I2C devices
i2cdetect -y 1
# Should show 0x70 (TCA9548A multiplexer)
```

**Expected Output:**
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: 70 -- -- -- -- -- -- --
```

---

## Step 3: Software Installation (5 minutes)

### Clone and Install
```bash
# Navigate to your projects directory
cd ~

# Clone the repository (or download and extract)
git clone <repository-url> desk_controler
cd desk_controler

# Install Python dependencies
pip3 install -r requirements.txt

### Verify Installation
```bash
# Check Python version
python3 --version
# Should be 3.7 or higher

# Verify dependencies installed
pip3 list | grep -E 'adafruit|pyserial'


 ```

## Step 3: Software Installation (5 minutes) ---> Step by Step

This step installs the project and its required Python packages in a safe, isolated environment.

## 1. Open a Terminal

 macOS: Applications → Utilities → Terminal

 Linux: Open your terminal app

 Windows: Open PowerShell (recommended)

## 2. Go to Your Home Directory

 This is a safe place to keep projects.

 cd ~

## 3. Clone the Project Repository

 Replace <repository-url> with the actual repository URL.

 git clone <repository-url> desk_controller
 cd desk_controller


## If git is not installed, install it first:

 macOS: brew install git

 Ubuntu/Debian: sudo apt install git

 Windows: https://git-scm.com/downloads

## 4. Check Your Python Version
 python3 --version


 You should see Python 3.7 or higher.

 If that fails:

 Try python --version

 On Windows, make sure Python is installed from https://python.org
  and “Add Python to PATH” was checked during install.

## 5. Create a Virtual Environment (Strongly Recommended)

 This keeps project dependencies from affecting your system.

 python3 -m venv venv

 Activate it:

 macOS / Linux

 source venv/bin/activate


 Windows (PowerShell)

 venv\Scripts\Activate.ps1


 You should now see (venv) at the start of your terminal line.

## 6. Install Required Python Packages
 pip install --upgrade pip
 pip install -r requirements.txt


 Wait for the installation to finish (this may take a minute).

## 7. Verify the Installation
 Confirm key dependencies are installed:
 pip list


Look for:

 pyserial

 adafruit (or Adafruit-related packages)

 Optional automatic check (works on all systems):
 python - <<EOF
 import pkg_resources
 packages = ["pyserial", "adafruit"]
 for p in packages:
     found = any(p in d.project_name.lower() for d in pkg_resources.working_set)
     print(f"{p}: {'OK' if found else 'MISSING'}")
 EOF

```
---
```
## Step 4: First Run (2 minutes)

### Test Hardware Detection
```bash
python3 -c "
from hardware import init_i2c, init_mux, scan_i2c_channels
i2c = init_i2c()
tca = init_mux(i2c)
scan_i2c_channels(tca)
"
```

**Expected Output:**
```
Initializing I2C bus...
I2C Bus opened successfully
Initializing TCA9548A multiplexer...
TCA9548A initialized successfully

Scanning I2C channels...
Channel 0: ['0x29']  ← VL53L0X #1
Channel 1: ['0x29']  ← VL53L0X #2
Channel 2: ['0x53']  ← ADXL345
Channel 3: No devices
Channel 4: No devices
Channel 5: No devices
Channel 6: No devices
Channel 7: No devices
```

### Run Main Program
```bash
python3 main.py
```

---

## Step 5: Initial Calibration (3 minutes)

The first time you run the system, you'll need to calibrate the sensors.

### Calibration Process

1. **Prepare the System:**
   - Ensure actuators are fully retracted (shortest position)
   - Motors should be at rest
   - No obstructions under sensors

2. **Run Calibration:**
```bash
python3 -c "
from hardware import init_i2c, init_mux, init_vl53l0x, init_adxl345
from calibration import calibrate_vl53_sensors
import config

# Initialize hardware
i2c = init_i2c()
tca = init_mux(i2c)
sensors = {
    'vl53l0x_0': init_vl53l0x(tca, config.VL53_CHANNEL_1, 'VL53L0X #1'),
    'vl53l0x_1': init_vl53l0x(tca, config.VL53_CHANNEL_2, 'VL53L0X #2')
}

# Calibrate
calibration_data = calibrate_vl53_sensors(sensors)
print('Calibration complete!')
"
```

3. **Verify Calibration:**
```bash
# Check calibration file was created
cat vl53_calibration.json
```

**Sample Output:**
```json
{
  "vl53l0x_0": {
    "baseline_mm": 59.5,
    "samples": [59, 59, 59, 60, 60, 60, 60, 59, 60, 60],
    "timestamp": 1769491160.629408
  },
  "vl53l0x_1": {
    "baseline_mm": 58.8,
    "samples": [58, 58, 58, 59, 60, 59, 60, 59, 59, 58],
    "timestamp": 1769491160.629413
  }
}
```

---

## Step 6: Basic Operation Test

### Test Sensor Readings
```bash
python3 -c "
from hardware import *
from calibration import load_calibration, get_calibrated_reading
import config

# Initialize
i2c = init_i2c()
tca = init_mux(i2c)
sensors = {
    'vl53l0x_0': init_vl53l0x(tca, config.VL53_CHANNEL_1, 'VL53L0X #1'),
    'vl53l0x_1': init_vl53l0x(tca, config.VL53_CHANNEL_2, 'VL53L0X #2'),
    'adxl345': init_adxl345(tca)
}

# Load calibration
calibration = load_calibration()

# Read sensors
print(f\"Distance 1: {get_sensor_value(sensors, 'vl53l0x_0')} mm\")
print(f\"Distance 2: {get_sensor_value(sensors, 'vl53l0x_1')} mm\")
print(f\"Pitch Angle: {get_sensor_value(sensors, 'adxl345'):.2f}°\")

# Show calibrated reading
reading = get_calibrated_reading(sensors, 'vl53l0x_0', calibration)
print(f\"Offset from baseline: {reading['offset_mm']:.2f} mm\")
"
```

### Test Motor Control (Optional)
```bash
python3 -c "
from hardware import *
from motor_control import move_station_distance, emergency_stop
import config

# Initialize
i2c = init_i2c()
tca = init_mux(i2c)
sensors = {'vl53l0x_0': init_vl53l0x(tca, 0, 'VL53L0X #1')}
ser = init_serial()

# Small test movement (10mm)
print('Moving 10mm...')
move_station_distance(sensors, 'vl53l0x_0', 70, ser, timeout=10)

# Stop
emergency_stop(ser)
print('Test complete!')
"
```

---

## You're Ready!

Your desk controller is now set up and calibrated. Here are some next steps:

### Basic Usage Examples

**Read Current Position:**
```python
from hardware import *
import config

i2c = init_i2c()
tca = init_mux(i2c)
sensor = init_vl53l0x(tca, config.VL53_CHANNEL_1, "VL53L0X #1")

distance = get_sensor_value({'vl53l0x_0': sensor}, 'vl53l0x_0')
print(f"Current position: {distance} mm")
```

**Move to Specific Height:**
```python
from hardware import *
from motor_control import move_station_distance
import config

# Initialize
i2c = init_i2c()
tca = init_mux(i2c)
sensor = init_vl53l0x(tca, config.VL53_CHANNEL_1, "VL53L0X #1")
ser = init_serial()

# Move to 150mm
move_station_distance({'vl53l0x_0': sensor}, 'vl53l0x_0', 150, ser)
```

**Emergency Stop:**
```python
from hardware import init_serial
from motor_control import emergency_stop

ser = init_serial()
emergency_stop(ser)  # Stops all motors immediately
```

### Useful Commands

```bash
# Run full system
python3 main.py

# Re-calibrate sensors
python3 -c "from calibration import *; calibrate_vl53_sensors(sensors)"

# Test hardware
python3 run_tests.py --quick

# View calibration data
cat vl53_calibration.json
```

---

## Common Issues & Solutions

### Issue: I2C Not Detected
**Solution:**
```bash
# Check I2C is enabled
sudo raspi-config  # Enable I2C again

# Add user to i2c group
sudo usermod -a -G i2c $USER
# Reboot after this
sudo reboot
```

### Issue: No Devices Found on I2C Scan
**Solution:**
- Check all wiring connections
- Verify 3.3V power is connected
- Make sure SDA/SCL are not swapped
- Check for loose connections

### Issue: Serial Port Error
**Solution:**
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
sudo reboot

# Verify serial port exists
ls /dev/serial*
```

### Issue: Import Errors
**Solution:**
```bash
# Reinstall dependencies
pip3 install -r requirements.txt --force-reinstall

# Or install individually
pip3 install adafruit-blinka adafruit-circuitpython-vl53l0x
```

### Issue: Sensor Timeout
**Solution:**
- Check sensor wiring
- Add I2C pullup resistors if needed (4.7kΩ)
- Try reducing I2C speed in config
- Check for shorts or damaged sensors

---

## Next Steps

Once you're up and running, explore these resources:

1. **[README.md](README.md)** - Full documentation and API reference
2. **[README_TESTS.md](README_TESTS.md)** - Testing guide
3. **[config.py](config.py)** - Customize settings
4. **[motor_control.py](motor_control.py)** - Motor control functions
5. **[calibration.py](calibration.py)** - Calibration functions

### Customize Your Setup

Edit `config.py` to adjust:
- Movement limits (MIN/MAX position)
- I2C retry settings
- Serial port configuration
- Timeout values

```python
# Example customization in config.py
MIN_POSITION = 30     # Minimum safe position
MAX_POSITION = 400    # Maximum safe position
I2C_RETRIES = 5       # More retries for reliability
```

---

## Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the [full README.md](README.md)
3. Run diagnostic tests: `python3 run_tests.py --quick`
4. Check hardware connections
5. Verify I2C devices: `i2cdetect -y 1`

---

## Quick Reference Card

| Action | Command |
|--------|---------|
| Run system | `python3 main.py` |
| Calibrate | See Step 5 above |
| Test hardware | `python3 run_tests.py --quick` |
| Check I2C | `i2cdetect -y 1` |
| Emergency stop | Call `emergency_stop(ser)` in code |
| View calibration | `cat vl53_calibration.json` |

---

**Congratulations! Your desk controller is ready to use! 🎊**

For detailed documentation, see [README.md](README.md)
