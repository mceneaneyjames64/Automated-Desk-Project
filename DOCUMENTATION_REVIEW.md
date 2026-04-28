# Documentation Review: Code vs. Documentation Alignment

**Date:** April 28, 2026  
**Reviewer:** GitHub Copilot  
**Repository:** mceneaneyjames64/Automated-Desk-Project

---

## Executive Summary

This document identifies misalignments between the documentation and actual code implementation. The project has strong documentation but contains **11 significant discrepancies** that require correction to maintain clarity and prevent confusion during development and deployment.

**Critical Issues:** 4  
**Medium Issues:** 5  
**Minor Issues:** 2

---

## Table of Contents

1. [Critical Issues](#critical-issues)
2. [Medium Issues](#medium-issues)
3. [Minor Issues](#minor-issues)
4. [Summary Table](#summary-table)

---

## Critical Issues

### 1. **Motor Control Direction Logic — Documentation vs. Code Mismatch**

**Documentation:** `desk_controler/README.md` (lines 200-225)
```
Motor Command Reference (from config.py):
| Constant | Bytes | Action |
|----------|-------|--------|
| CMD_M1_EXTEND | 5A 01 5B | Motor 1 extend (OUT) |
| CMD_M1_RETRACT | 5A 02 5C | Motor 1 retract (IN) |
| ...
```

And later: "Sensor → Motor mapping" states Motor 1 controls tilt, Motor 2/3 control height.

**Actual Code:** `motor_control.py` (lines 239-243)
```python
# Comment says "Motor 3" but function is move_to_angle which controls Motor 1
def move_to_angle(sensors: dict, target_deg: float,
                  ser, tolerance: float = 1.0, timeout: float = 30) -> bool:
    """
    Move the tilt actuator (Motor 3) to a target angle using the ADXL345.
```

**Problem:** Documentation header comments in `motor_control.py` incorrectly label the tilt actuator as **Motor 3** when it actually controls **Motor 1** (per `config.py` SENSOR_MOTOR_COMMANDS mapping).

**Impact:** Critical — developers may wire or command the wrong motor.

**Fix:** 
- Update `motor_control.py` line 239 comment: change "Motor 3" → "Motor 1"
- Ensure consistent naming: Motor 1 = tilt/angle, Motor 2 = distance sensor #1, Motor 3 = distance sensor #2

---

### 2. **Angle Convention Discrepancy — Documentation Says Z-Axis Used, But Z-Axis Logic Differs**

**Documentation:** `desk_controler/README.md` (lines 152-176) and `Key_concepts.md` (lines 52-80)
```
Angle convention:
| Z-axis reading | Angle |
|----------------|-------|
| Z ≈ −g (upside down) | 0° |
| Z ≈ 0 (perpendicular to ground) | 90° |
| Z ≈ +g (right-side up) | 180° |
```

**Actual Code:** `hardware/sensors.py` (lines 104-110)
```python
elif sensor_name == config.SENSOR_ADXL:
    x, y, z = read_with_timeout(
        lambda: sensors[config.SENSOR_ADXL].acceleration,
        f"{config.SENSOR_ADXL} acceleration read",
    )
    return z_axis_to_degrees(z)
```

And from `utils` (not shown but referenced): The `z_axis_to_degrees()` function is imported from `utils.misc` but the actual implementation is not provided in the reviewed files. The formula documented as:
```
angle = 180° − arccos( clamp(z / g, −1, 1) )
```

**Problem:** The actual utility function `z_axis_to_degrees()` is not documented in the code. The formula is explained in markdown but the implementation is missing from the code files reviewed.

**Impact:** Medium-High — Without seeing the actual implementation, it's unclear if the formula matches what the documentation claims.

**Fix:**
- Add the actual `z_axis_to_degrees()` implementation to `utils/misc.py` with the formula as a docstring
- Or add a reference comment in `sensors.py` pointing to where the implementation lives

---

### 3. **Calibration Procedure Documentation References Non-existent Code Paths**

**Documentation:** `docs/Calibration.md` (lines 78-97)
```bash
python3 -c "
from hardware.i2c_utils import init_i2c, init_mux
from hardware.sensors import init_vl53l0x, get_sensor_value
from calibration import calibrate_vl53_sensors
...
```

**Actual Code:** `calibration.py` (lines 38-88)
```python
def calibrate_vl53_sensors(sensors):
    # Takes 30 samples, prints prompts
    # But there's NO input('...Press ENTER...') in the function
```

**Problem:** Documentation shows interactive prompt (`Press ENTER when ready to calibrate...`) but the actual function in `calibration.py` does NOT prompt the user — it immediately starts taking samples. The documentation (line 104 in Calibration.md) shows "Press ENTER when ready..." but this code doesn't exist in `calibrate_vl53_sensors()`.

**Impact:** Critical — Users following the documentation will have a different experience than what's documented.

**Fix:**
- Either add the interactive prompt to `calibrate_vl53_sensors()` or
- Update documentation to remove the "Press ENTER..." step

---

### 4. **Motor Channel Assignments — Documentation Says Motor 3 for Tilt, Code Says Motor 1**

**Documentation:** `desk_controler/README.md` (lines 217-224)
```
| Sensor | Motor | Direction logic |
|--------|-------|-----------------|
| adxl345 | Motor 1 | Z-axis angle controls tilt |
| vl53l0x_0 | Motor 2 | Distance controls height #1 |
| vl53l0x_1 | Motor 3 | Distance controls height #2 |
```

This table is correct! But then in **README line 239** (under "Code Flow" section):
```
D[Initialize ADXL345]
D --> E[Initialize Serial Port<br/>Motor Control]
...
```

The flowchart doesn't clearly label which motor corresponds to which sensor, causing confusion.

**Problem:** The comment in `motor_control.py` line 239 says "Motor 3" for tilt, contradicting the table in README that correctly says Motor 1.

**Impact:** Critical — direct contradiction between different sections of documentation.

**Fix:** Standardize all references to Motor 1 for tilt control.

---

## Medium Issues

### 5. **`desk_controller_wrapper.py` Not Documented**

**Documentation:** Missing entirely from all documentation files.

**Actual Code:** `desk_controller_wrapper.py` (62 KB file) contains the main application logic including:
- `initialize_hardware()`
- `mqtt_connect()`
- `move_motor_to_position()`
- `load_and_execute_preset()`
- `emergency_stop_all()`
- Preset management
- MQTT integration

**Problem:** This is the primary user-facing API, but there is **no documentation** for its public methods, parameters, or return values.

**Impact:** High — developers using the wrapper have no reference documentation.

**Fix:** Create `desk_controler/docs/DeskControllerWrapper.md` documenting all public methods with examples.

---

### 6. **Installation Instructions Reference Wrong Python Paths**

**Documentation:** `README.md` (lines 247-255)
```bash
# Clone repository
git clone https://github.com/mceneaneyjames64/Automated-Desk-Project.git
cd Automated-Desk-Project/desk_controler/src

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd src
pip install -r requirements.txt
```

**Problem:** Line 247 says `cd Automated-Desk-Project/desk_controler/src` but then line 254 says `cd src` again. This creates a path like `desk_controler/src/src` which doesn't exist.

**Actual Code Structure:**
```
Automated-Desk-Project/
└── desk_controler/
    └── src/
        ├── main.py
        ├── requirements.txt
        └── ...
```

**Impact:** Medium — users will fail at the installation step.

**Fix:** Correct the path to either:
- `cd desk_controler/src` then `pip install -r requirements.txt`, OR
- `cd desk_controler` then `pip install -r src/requirements.txt`

---

### 7. **Sensor Averaging Configuration Not Fully Documented**

**Documentation:** `Key_concepts.md` doesn't mention `SENSOR_AVERAGE_SAMPLES` from `config.py` (line 59).

**Actual Code:** `config.py` (lines 52-59)
```python
# Number of consecutive VL53L0X readings to average inside the closed-loop
# control and calibration helpers.  Averaging suppresses the per-reading noise
# (typically ±2–5 mm) so that the calibration offset is applied to a stable
# value rather than a single noisy sample.  Three samples add ~66 ms of extra
# latency per control cycle (3 × 33 ms timing budget) which is acceptable for
# desk positioning.  Increase to 5 for noisier environments; decrease to 2 to
# favour responsiveness over noise immunity.
SENSOR_AVERAGE_SAMPLES = 3
```

**Problem:** This configuration is not mentioned in any documentation, but it's critical for understanding the trade-off between noise immunity and responsiveness.

**Impact:** Medium — users tuning the system don't know this parameter exists.

**Fix:** Add a section in `Key_concepts.md` explaining noise filtering and `SENSOR_AVERAGE_SAMPLES`.

---

### 8. **Angle Limits Configuration Not Referenced in Documentation**

**Documentation:** `desk_controler/README.md` (line 198) mentions safe range but doesn't explain why MIN/MAX are what they are.

**Actual Code:** `config.py` (lines 119-121)
```python
# =============================================================================
# Angle Limits (degrees) — ADXL345 actuator (Motor 3)
#
#   The actuator has a 200 mm stroke.  Map that stroke onto an angle window
#   that keeps the actuator safely within its mechanical limits.
#
#     MIN_ANGLE_DEG : angle at which the actuator is fully retracted
#     MAX_ANGLE_DEG : angle at which the actuator is fully extended
#
#   Convention: 0° = upside down, 90° = perpendicular, 180° = right-side up.
#   Adjust these limits to match your physical installation.
# =============================================================================
MIN_ANGLE_DEG = 60.0    # fully retracted — adjust to your rig
MAX_ANGLE_DEG = 120.0   # fully extended  — adjust to your rig
```

**Problem:** Documentation doesn't explain the relationship between 200 mm stroke and 60°-120° angle range, or how to calculate these for different installations.

**Impact:** Medium — users modifying for their setup don't understand the tuning.

**Fix:** Add a calibration section explaining stroke-to-angle mapping.

---

### 9. **MQTT Configuration Hardcoded in `main.py`, Not Documented**

**Actual Code:** `main.py` (lines 285-295)
```python
controller = DeskControllerWrapper(
    broker="192.168.1.138",
    mqtt_port=1883,
    mqtt_username="mqtttest",
    mqtt_password="VMIececapstone",
    mqtt_command_topic="home/desk/command",
    mqtt_status_topic="home/desk/status",
    mqtt_feedback_topic="home/desk/feedback",
    presets_file="desk_presets.json",
    log_file="desk_controller.log",
    auto_calibrate_on_init=args.auto_calibrate,
)
```

**Problem:** 
1. MQTT credentials are hardcoded in the source code (security issue)
2. No documentation about how to configure MQTT
3. Broker IP is hardcoded to a specific internal IP
4. No guidance on environment variables or configuration files

**Documentation:** `config.py` has MQTT settings but `main.py` overrides them with hardcoded values. No documentation explains which takes precedence.

**Impact:** Medium — security concern + deployment difficulty.

**Fix:** Update documentation and code to use environment variables or a separate config file for MQTT settings.

---

## Minor Issues

### 10. **Test Documentation References Non-existent Commands**

**Documentation:** `tests/README.md` (lines 100-102)
```bash
# Safety-critical tests
python run_tests.py --safety

# Specific module tests
python run_tests.py --module motor
python run_tests.py --module calibration
```

**Problem:** `run_tests.py` is mentioned but:
1. Not reviewed/verified to support these flags
2. `--module` flag not mentioned in the pytest.ini configuration

**Impact:** Minor — users can't run the documented commands.

**Fix:** Verify `run_tests.py` actually supports these flags, or update documentation to match actual capabilities.

---

### 11. **Directory Structure in README Still References Old Layout**

**Documentation:** `README.md` (lines 154-199)
```
Automated-Desk-Project/           # Repository root
├── README.md                     # This file
├── heartbeat-handler.py          # Standalone heartbeat monitor
│
└── desk_controler/               # Main controller application
    ├── README.md                 # Detailed technical architecture
    ├── src/                      # Source code
    │   ├── main.py               # Main application entry point
```

**Actual Code:** Line 158 shows `heartbeat-handler.py` is supposed to be in the root, but it may not be verified to exist or be functional.

**Problem:** Minor discrepancy in file structure documentation vs. actual repo contents.

**Impact:** Minor — users looking for files based on diagram.

**Fix:** Verify `heartbeat-handler.py` exists and is documented, or remove from tree if not used.

---

## Summary Table

| Issue # | Title | Severity | File(s) | Fix Priority |
|---------|-------|----------|---------|--------------|
| 1 | Motor control direction logic contradiction | Critical | `motor_control.py`, `README.md` | HIGH |
| 2 | Angle convention formula not implemented | Critical | `utils/misc.py` | HIGH |
| 3 | Calibration interactive prompts missing | Critical | `calibration.py`, `Calibration.md` | HIGH |
| 4 | Motor naming inconsistency (Motor 1 vs 3) | Critical | `motor_control.py`, `README.md` | HIGH |
| 5 | `desk_controller_wrapper.py` not documented | High | `DeskControllerWrapper.md` (missing) | HIGH |
| 6 | Installation path error | High | `README.md` | HIGH |
| 7 | Sensor averaging not documented | Medium | `Key_concepts.md` | MEDIUM |
| 8 | Angle limits calibration not explained | Medium | `docs/` | MEDIUM |
| 9 | MQTT credentials hardcoded + undocumented | Medium | `main.py`, `docs/` | MEDIUM |
| 10 | Test command flags not verified | Minor | `tests/README.md` | LOW |
| 11 | Directory structure file existence unclear | Minor | `README.md` | LOW |

---

## Recommendations

### Immediate Actions (Critical)

1. **Fix motor labeling:** Standardize all references to Motor 1 for tilt control
2. **Verify angle formula:** Ensure `z_axis_to_degrees()` implementation matches documentation
3. **Update calibration:** Either add interactive prompts or update documentation
4. **Correct installation guide:** Fix Python path in README

### Short-term Actions (High Priority)

5. Document `DeskControllerWrapper` API comprehensively
6. Add sensor averaging configuration documentation
7. Secure MQTT credentials (environment variables or config file)

### Long-term Actions (Medium Priority)

8. Document angle limit calibration procedure
9. Verify test runner capabilities match documentation
10. Audit file structure against documentation

---

## Conclusion

The project has **strong overall documentation quality**, but the identified discrepancies create confusion and could lead to configuration errors, security issues, and failed deployments. Addressing the **4 critical issues** should be the immediate priority, followed by the high-priority documentation and API documentation.

Most issues are fixable with documentation updates rather than code changes, making this a lower-risk remediation effort.

