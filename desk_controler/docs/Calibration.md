# Calibration Guide

Complete procedures for calibrating the VL53L0X distance sensors in the Automated Desk Controller.

## Table of Contents

- [Overview](#overview)
- [When to Calibrate](#when-to-calibrate)
- [Prerequisites](#prerequisites)
- [Calibration Procedure](#calibration-procedure)
- [Calibration Data Structure](#calibration-data-structure)
- [Verifying Calibration](#verifying-calibration)
- [Recalibration](#recalibration)
- [Troubleshooting Calibration Issues](#troubleshooting-calibration-issues)
- [Best Practices](#best-practices)

---

## Overview

The VL53L0X sensors measure absolute distance to the nearest object in their line of sight.
Calibration determines the **software offset** that converts each raw reading into a
position relative to the fully retracted (home) position.

The offset is calculated as:

```
offset = -(raw_average - known_distance)
```

Where `known_distance` is `0 mm` (the actuator is fully retracted during calibration).
After calibration, every corrected reading is:

```
corrected_mm = raw_mm + offset
```

Offsets are saved into `config.OFFSET` inside `config.py` and are reloaded automatically
on the next run. No separate JSON file is used.

---

## When to Calibrate

Recalibrate whenever any of the following occur:

- **First installation** — no offsets exist yet
- **Sensor repositioning** — sensor or mount moved
- **Actuator reassembly** — mechanical changes affecting the rest position
- **Persistent drift** — corrected readings consistently read non-zero at the retracted position
- **Sensor replacement** — new sensor has different baseline

---

## Prerequisites

Before starting calibration:

1. Hardware fully assembled and wired (see [Quick Start Guide](quickstart_guide.md))
2. I2C enabled and all sensors detected (`i2cdetect -y 1` shows `0x70`)
3. Python dependencies installed (`pip install -r requirements.txt`)
4. **Actuators fully retracted** — this is the reference position (0 mm)
5. No obstructions in the sensor beam path

---

## Calibration Procedure

### Step 1 — Fully Retract All Actuators

Manually retract all linear actuators to their minimum (home) position before proceeding.
This is the physical reference point that corresponds to 0 mm in the software.

### Step 2 — Run Calibration

Navigate to the source directory and launch the calibration routine:

```bash
cd desk_controler/src
python3 -c "
from hardware.i2c_utils import init_i2c, init_mux
from hardware.sensors import init_vl53l0x, get_sensor_value
from calibration import calibrate_vl53_sensors
import config

# Initialize hardware
i2c = init_i2c()
tca = init_mux(i2c)
sensors = {
    config.SENSOR_VL53_0: init_vl53l0x(tca, config.VL53_CHANNEL_0, 'VL53L0X #1'),
    config.SENSOR_VL53_1: init_vl53l0x(tca, config.VL53_CHANNEL_1, 'VL53L0X #2'),
}

# Run calibration
calibrate_vl53_sensors(sensors)
"
```

### Step 3 — Follow the On-Screen Prompts

The calibration routine will:

1. Print a reminder to retract the actuators
2. Wait for you to press **ENTER**
3. Take **30 samples** from each sensor (one every 0.1 s)
4. Calculate and display the offset for each sensor
5. Write the offsets to `config.py`

**Example output:**

```
==================================================
VL53L0X SENSOR CALIBRATION
==================================================

Ensure actuators are fully retracted before continuing.
Press ENTER when ready to calibrate...

Calibrating VL53L0X #1...
  Known distance: 0 mm
  Sample 1/30: 121 mm
  Sample 2/30: 121 mm
  ...
  Sample 30/30: 120 mm
  Average raw reading: 121.03 mm
  Error vs known distance: +121.03 mm
  Software offset: -121.03 mm

Calibrating VL53L0X #2...
  ...
  Software offset: -84.10 mm

==================================================
CALIBRATION COMPLETE
==================================================
  vl53l0x_0: raw avg 121.03 mm | error +121.03 mm | offset -121.03 mm
  vl53l0x_1: raw avg  84.10 mm | error  +84.10 mm | offset  -84.10 mm
  Data saved to config.OFFSET
```

### Step 4 — Verify Calibration

Check that `config.py` now contains the updated offsets:

```bash
grep "^OFFSET" desk_controler/src/config.py
```

Expected output (values will differ per installation):

```python
OFFSET = {'vl53l0x_0': -121.03, 'vl53l0x_1': -84.1}
```

---

## Calibration Data Structure

Offsets are stored in `config.py` as a plain Python dictionary:

```python
# config.py (auto-generated section)
OFFSET = {'vl53l0x_0': -121.0, 'vl53l0x_1': -84.1}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `vl53l0x_0` | float (mm) | Software offset for distance sensor #1 |
| `vl53l0x_1` | float (mm) | Software offset for distance sensor #2 |

The offsets are negative when the sensors read a positive distance at the retracted position
(which is the typical case — the sensor face never sits at exactly 0 mm from the target).

---

## Verifying Calibration

After calibration, confirm corrected readings are near 0 mm at the retracted position:

```bash
cd desk_controler/src
python3 -c "
from hardware.i2c_utils import init_i2c, init_mux
from hardware.sensors import init_vl53l0x
from calibration import load_calibration, get_calibrated_reading
import config

i2c = init_i2c()
tca = init_mux(i2c)
sensors = {
    config.SENSOR_VL53_0: init_vl53l0x(tca, config.VL53_CHANNEL_0, 'VL53L0X #1'),
    config.SENSOR_VL53_1: init_vl53l0x(tca, config.VL53_CHANNEL_1, 'VL53L0X #2'),
}

calibration = load_calibration()
for name in [config.SENSOR_VL53_0, config.SENSOR_VL53_1]:
    reading = get_calibrated_reading(sensors, name, calibration)
    print(f'{name}: raw={reading[\"raw_mm\"]} mm  corrected={reading[\"corrected_mm\"]} mm  offset={reading[\"offset_mm\"]} mm')
"
```

**Good result** (actuators retracted): corrected reading near 0 mm (within ±3 mm).

---

## Recalibration

To recalibrate, simply re-run the calibration procedure. The new offsets will overwrite the
existing values in `config.py`. No manual file editing is required.

**Tip:** If calibration results vary significantly between runs, check for vibration,
loose sensor mounts, or objects in the sensor beam path.

---

## Troubleshooting Calibration Issues

### Offset values are very large (> 500 mm)

**Cause:** Sensor is not pointing at the desk surface, or an obstruction is very close.  
**Fix:** Check sensor orientation and ensure the beam path is clear before calibrating.

### Corrected readings drift upward over time

**Cause:** Sensor mount has shifted, or temperature changes are affecting the baseline.  
**Fix:** Re-run calibration with the actuators retracted.

### `RuntimeError: No calibration data available`

**Cause:** `config.OFFSET` is missing or empty; calibration has not been run yet.  
**Fix:** Run the calibration procedure (Step 2 above).

### Samples vary by more than ±5 mm during calibration

**Cause:** Vibration, loose wiring, or I2C errors causing noisy readings.  
**Fix:**
- Check I2C wiring and connections
- Ensure the desk and sensors are stationary during calibration
- Increase `CALIBRATION_SAMPLES` in `calibration.py` for a more stable average

### `config.py` is not updated after calibration

**Cause:** Calibration script is not running from the `src/` directory, so `config.py`
cannot be found by the relative file path.  
**Fix:** Always run calibration from `desk_controler/src/`:

```bash
cd desk_controler/src
python3 -c "..."
```

---

## Best Practices

- Always retract actuators **fully** before calibrating — partial retraction gives wrong offsets
- Run calibration at **room temperature** to minimise thermal drift
- Take calibration samples on a **stable surface** — vibration increases noise
- **Document your offsets** (e.g., in a setup log) so you can detect unexpected changes
- Recalibrate after any mechanical reassembly or sensor replacement

---

## See Also

- [Quick Start Guide](quickstart_guide.md) — Initial hardware and software setup
- [Key Concepts](Key_concepts.md) — How VL53L0X sensors and closed-loop control work
- [Troubleshooting Guide](Troubleshooting%20Guide.md) — General hardware and software issues
- [desk_controler/README.md](../README.md) — Full technical architecture reference
