"""
Calibration routine for VL53L0X sensors using software offset correction.

The VL53L0X Adafruit library does not support writing to the hardware offset
register at runtime. Instead, this module measures the sensor error against a
known reference distance and saves a software offset that is applied to every
reading via get_calibrated_reading().
"""
import time
import config
import pprint
from hardware import get_sensor_value

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
	input("Press ENTER when ready to calibrate...\n")

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
