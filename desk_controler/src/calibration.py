"""
Calibration routine for VL53L0X sensors using software offset correction.

The VL53L0X Adafruit library does not support writing to the hardware offset
register at runtime. Instead, this module measures the sensor error against a
known reference distance and saves a software offset that is applied to every
reading via get_calibrated_reading().
"""
import time
import json
from pathlib import Path
from hardware import get_sensor_value


CALIBRATION_FILE = "vl53_calibration.json"
CALIBRATION_SAMPLES = 10
SAMPLE_DELAY = 0.1

# Place a flat target exactly this far from each sensor before calibrating.
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

    Place a flat target exactly KNOWN_DISTANCE_MM in front of each sensor.
    The function averages CALIBRATION_SAMPLES readings, computes the error
    vs the known distance, and saves a software offset to CALIBRATION_FILE.

    That offset is later applied by get_calibrated_reading() to correct
    every reading transparently.

    Args:
        sensors (dict): Must contain 'vl53l0x_0' and 'vl53l0x_1' keys mapped
                        to initialised adafruit_vl53l0x.VL53L0X objects.

    Returns:
        dict: Calibration data for both sensors.
    """
    print("\n" + "=" * 50)
    print("VL53L0X SENSOR CALIBRATION")
    print("=" * 50)
    print(f"\nPlace a flat target exactly {KNOWN_DISTANCE_MM} mm in front of EACH sensor.")
    input("Press ENTER when ready to calibrate...\n")

    calibration_data = {}

    sensor_configs = [
        ("vl53l0x_0", "VL53L0X #1"),
        ("vl53l0x_1", "VL53L0X #2"),
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
    print(f"  Data saved to: {CALIBRATION_FILE}\n")

    return calibration_data


def save_calibration(calibration_data):
    """Save calibration data to JSON file."""
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(calibration_data, f, indent=2)
    print(f"\nCalibration data saved to {CALIBRATION_FILE}")


def load_calibration():
    """
    Load calibration data from file.

    Returns:
        dict or None: Calibration data, or None if the file doesn't exist.
    """
    cal_path = Path(CALIBRATION_FILE)
    if not cal_path.exists():
        print(f"Warning: Calibration file {CALIBRATION_FILE} not found")
        return None

    try:
        with open(CALIBRATION_FILE, "r") as f:
            calibration_data = json.load(f)
        print(f"Loaded calibration data from {CALIBRATION_FILE}")
        return calibration_data
    except Exception as e:
        print(f"Error loading calibration file: {e}")
        return None


def get_calibrated_reading(sensors, sensor_name, calibration_data):
    """
    Get a corrected sensor reading by applying the stored software offset.

    Args:
        sensors (dict): Dictionary of sensor objects.
        sensor_name (str): 'vl53l0x_0' or 'vl53l0x_1'.
        calibration_data (dict): Loaded calibration data.

    Returns:
        dict: {
            'raw_mm'      : uncorrected reading from sensor,
            'corrected_mm': raw_mm + offset (the value to use),
            'offset_mm'   : the software offset applied,
        }
    """
    if calibration_data is None:
        raise RuntimeError("No calibration data available. Run calibration first.")

    if sensor_name not in calibration_data:
        raise RuntimeError(f"Sensor '{sensor_name}' not found in calibration data.")

    raw = get_sensor_value(sensors, sensor_name)
    offset = calibration_data[sensor_name]["offset_mm"]
    corrected = raw + offset

    return {
        "raw_mm": raw,
        "corrected_mm": round(corrected, 3),
        "offset_mm": offset,
    }


def print_calibration_info(calibration_data):
    """Print stored calibration information."""
    if calibration_data is None:
        print("No calibration data available")
        return

    print("\n" + "=" * 50)
    print("CALIBRATION DATA")
    print("=" * 50)

    for sensor_name, data in calibration_data.items():
        print(f"\n{sensor_name.upper()}:")
        print(f"  Known reference distance : {data.get('known_distance_mm', 'N/A')} mm")
        print(f"  Raw average at cal time  : {data.get('raw_average_mm', 'N/A'):.2f} mm")
        print(f"  Error                    : {data.get('error_mm', 'N/A'):+.3f} mm")
        print(f"  Software offset          : {data.get('offset_mm', 'N/A'):+.3f} mm")
        print(f"  Timestamp                : {time.ctime(data['timestamp'])}")
        if "samples" in data:
            s = data["samples"]
            print(f"  Sample range             : {min(s)} - {max(s)} mm")

    print("\n" + "=" * 50 + "\n")
