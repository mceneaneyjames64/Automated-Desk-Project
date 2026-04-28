"""
Calibration routine for VL53L0X sensors using software offset correction.

The VL53L0X Adafruit library does not support writing to the hardware offset
register at runtime. Instead, this module measures the sensor error against a
known reference distance and saves a software offset that is applied to every
reading via get_calibrated_reading().
"""
import logging
import time
import config
import pprint
from hardware import get_sensor_value

_log = logging.getLogger(__name__)

CALIBRATION_SAMPLES = 30
SAMPLE_DELAY = 0.1

# KNOWN_DISTANCE_MM is the true distance from the sensor face to the target
# during calibration. Set to 0 when calibrating at the fully retracted position
# (sensor reads its resting distance naturally; offset corrects that to zero).
KNOWN_DISTANCE_MM = 0

def _read_raw_average(sensors, sensor_key, num_samples=CALIBRATION_SAMPLES):
	"""Take multiple readings and return (average, list_of_samples)."""
	readings = []
	for i in range(num_samples):
		reading = get_sensor_value(sensors, sensor_key)
		readings.append(reading)
		print(f"  Sample {i + 1}/{num_samples}: {reading} mm")
		time.sleep(SAMPLE_DELAY)
	average = sum(readings) / len(readings)
	print(f"  Average raw reading: {average:.2f} mm")
	return average, readings


def calibrate_vl53_sensors(sensors):
	"""
    Calibrate VL53L0X sensors against a known reference distance.
    """
	print("\n" + "=" * 50)
	print("VL53L0X SENSOR CALIBRATION")
	print("=" * 50)
	print("\nEnsure actuators are fully retracted before continuing.")

	calibration_data = {}

	sensor_configs = [
		(config.SENSOR_VL53_0, "VL53L0X #1"),
		(config.SENSOR_VL53_1, "VL53L0X #2"),
	]

	for sensor_key, label in sensor_configs:
		print(f"\nCalibrating {label}...")
		print(f"  Known distance: {KNOWN_DISTANCE_MM} mm")

		average_raw, samples = _read_raw_average(sensors, sensor_key)

		error = average_raw - KNOWN_DISTANCE_MM
		offset = -error  # add this to future raw readings to correct them

		print(f"  Error vs known distance : {error:+.2f} mm")
		print(f"  Software offset         : {offset:+.2f} mm")

		calibration_data[sensor_key] = {
			"known_distance_mm": KNOWN_DISTANCE_MM,
			"raw_average_mm": round(average_raw, 3),
			"error_mm": round(error, 3),
			"offset_mm": round(offset, 3),
			"samples": samples,
			"timestamp": time.time(),
		}

	save_calibration(calibration_data)

	print("\n" + "=" * 50)
	print("CALIBRATION COMPLETE")
	print("=" * 50)
	for sensor_key, data in calibration_data.items():
		print(
			f"  {sensor_key}: raw avg {data['raw_average_mm']:.2f} mm | "
			f"error {data['error_mm']:+.3f} mm | "
			f"offset {data['offset_mm']:+.3f} mm"
		)
	print(f"  Data saved to config.OFFSET\n")

	return calibration_data


def calibrate_automatic(sensors, retract_fn=None, max_retries=3):
	"""
	Run the full calibration flow automatically without user interaction.

	Parameters
	----------
	sensors : dict
		Initialized sensor objects (as returned by hardware init helpers).
	retract_fn : callable, optional
		Zero-argument callable that retracts all motors to the home position
		before calibration begins.  Should return True on success, False on
		failure.  When *None* no retraction is attempted.
	max_retries : int
		Maximum number of calibration attempts before giving up (default: 3).
		Retries use exponential back-off delays: 1 s before the 2nd attempt,
		2 s before the 3rd, 4 s before the 4th, etc.

	Returns
	-------
	dict or None
		Calibration data dictionary (same shape as ``calibrate_vl53_sensors``)
		on success, or *None* if all attempts failed.
	"""
	# Skip if calibration data already exists
	if load_calibration():
		_log.info("Calibration data already exists — skipping automatic calibration.")
		return load_calibration()

	_log.info("Starting automatic calibration routine...")

	# Retract motors to known home position before measuring
	if retract_fn is not None:
		_log.info("Retracting motors to home position...")
		if not retract_fn():
			_log.error("Motor retraction failed; cannot proceed with calibration.")
			return None

	# Attempt calibration with exponential back-off retry
	for attempt in range(max_retries):
		delay = 2 ** attempt  # delay before next retry: 1 s, 2 s, 4 s, …
		try:
			_log.info("Calibration attempt %d/%d...", attempt + 1, max_retries)
			calibration_data = calibrate_vl53_sensors(sensors)
			_log.info("Automatic calibration completed successfully.")
			return calibration_data
		except Exception as exc:
			_log.error("Calibration attempt %d failed: %s", attempt + 1, exc)
			if attempt < max_retries - 1:
				_log.info("Retrying in %ds...", delay)
				time.sleep(delay)

	# All retries exhausted — try to return to a safe (retracted) state
	if retract_fn is not None:
		try:
			retract_fn()
		except Exception:
			pass

	_log.error("Automatic calibration failed after %d attempt(s).", max_retries)
	return None


def save_calibration(calibration_data):
	"""Persists calibration offsets into config.py"""

	offsets = {
		sensor: data["offset_mm"]
		for sensor, data in calibration_data.items()
	}
	
	# Read existing config file
	with open("config.py", "r") as f:
		lines = f.readlines()
		
	# Replace OFFSET line if it exists
	found = False
	for i, line in enumerate(lines):
		if line.startswith("OFFSET"):
			lines[i] = f"OFFSET = {pprint.pformat(offsets)}\n"
			found = True
			break
	
	# If not found, append it
	if not found:
		lines.append("\n# Calibration Offsets (auto-generated)\n")
		lines.append(f"OFFSET = {pprint.pformat(offsets)}\n")
		
	# Write back safely
	with open("config.py", "w") as f:
		f.writelines(lines)
		
	print("\nOffsets written to config.py:")
	for k, v in offsets.items():
		print(f"	{k}: {v:+.3f} mm")
	
	# Also update runtime values
	config.OFFSET = offsets
	

def load_calibration():
	"""Load calibration data from config.OFFSET, or return None if not set."""
	if not hasattr(config, "OFFSET") or not config.OFFSET:
		return None
	# Reconstruct calibration_data shape from the flat offset dict
	data = {}
	for sensor_name, offset_mm in config.OFFSET.items():
		data[sensor_name] = {"offset_mm": offset_mm}
	return data


def get_calibrated_reading(sensors, sensor_name, calibration_data):
	"""Return raw and offset-corrected reading for sensor_name."""
	if not hasattr(config, "OFFSET") or not config.OFFSET:
		raise RuntimeError("No calibration data available. Run calibration first.")
	
	if sensor_name not in config.OFFSET:
		raise RuntimeError(f"Sensor '{sensor_name}' not found in config.OFFSET")
	
	raw = get_sensor_value(sensors, sensor_name)
	offset = config.OFFSET[sensor_name]
	corrected = raw + offset
	
	return {
		"raw_mm": raw,
		"corrected_mm": round(corrected, 3),
		"offset_mm": offset,
		}
