"""
Calibration routine for VL53L0X sensors at fully retracted position
"""
import time
import json
from pathlib import Path
from hardware import get_sensor_value


CALIBRATION_FILE = "vl53_calibration.json"
CALIBRATION_SAMPLES = 10
SAMPLE_DELAY = 0.1


def calibrate_vl53_sensors(sensors):
    """
    Calibrate VL53L0X sensors at fully retracted position
    
    This routine assumes actuators are at MIN_POSITION (fully retracted).
    It takes multiple samples and stores the baseline readings.
    
    Args:
        sensors (dict): Dictionary of sensor objects
        
    Returns:
        dict: Calibration data containing baseline readings
    """
    print("\n" + "="*50)
    print("VL53L0X SENSOR CALIBRATION")
    print("="*50)
    print("\nEnsure actuators are fully retracted before continuing!")
    input("Press ENTER when ready to calibrate...")
    
    calibration_data = {}
    
    # Calibrate VL53L0X #1
    print(f"\nCalibrating VL53L0X #1 (taking {CALIBRATION_SAMPLES} samples)...")
    vl53_0_readings = []
    for i in range(CALIBRATION_SAMPLES):
        reading = get_sensor_value(sensors, 'vl53l0x_0')
        vl53_0_readings.append(reading)
        print(f"  Sample {i+1}/{CALIBRATION_SAMPLES}: {reading} mm")
        time.sleep(SAMPLE_DELAY)
    
    vl53_0_baseline = sum(vl53_0_readings) / len(vl53_0_readings)
    print(f"  Average baseline: {vl53_0_baseline:.2f} mm")
    
    # Calibrate VL53L0X #2
    print(f"\nCalibrating VL53L0X #2 (taking {CALIBRATION_SAMPLES} samples)...")
    vl53_1_readings = []
    for i in range(CALIBRATION_SAMPLES):
        reading = get_sensor_value(sensors, 'vl53l0x_1')
        vl53_1_readings.append(reading)
        print(f"  Sample {i+1}/{CALIBRATION_SAMPLES}: {reading} mm")
        time.sleep(SAMPLE_DELAY)
    
    vl53_1_baseline = sum(vl53_1_readings) / len(vl53_1_readings)
    print(f"  Average baseline: {vl53_1_baseline:.2f} mm")
    
    # Store calibration data
    calibration_data = {
        'vl53l0x_0': {
            'baseline_mm': vl53_0_baseline,
            'samples': vl53_0_readings,
            'timestamp': time.time()
        },
        'vl53l0x_1': {
            'baseline_mm': vl53_1_baseline,
            'samples': vl53_1_readings,
            'timestamp': time.time()
        }
    }
    
    # Save to file
    save_calibration(calibration_data)
    
    print("\n" + "="*50)
    print("CALIBRATION COMPLETE")
    print("="*50)
    print(f"VL53L0X #1 baseline: {vl53_0_baseline:.2f} mm")
    print(f"VL53L0X #2 baseline: {vl53_1_baseline:.2f} mm")
    print(f"Data saved to: {CALIBRATION_FILE}\n")
    
    return calibration_data


def save_calibration(calibration_data):
    """Save calibration data to JSON file"""
    with open(CALIBRATION_FILE, 'w') as f:
        json.dump(calibration_data, f, indent=2)
    print(f"\nCalibration data saved to {CALIBRATION_FILE}")


def load_calibration():
    """
    Load calibration data from file
    
    Returns:
        dict: Calibration data or None if file doesn't exist
    """
    cal_path = Path(CALIBRATION_FILE)
    if not cal_path.exists():
        print(f"Warning: Calibration file {CALIBRATION_FILE} not found")
        return None
    
    try:
        with open(CALIBRATION_FILE, 'r') as f:
            calibration_data = json.load(f)
        print(f"Loaded calibration data from {CALIBRATION_FILE}")
        return calibration_data
    except Exception as e:
        print(f"Error loading calibration file: {e}")
        return None


def get_calibrated_reading(sensors, sensor_name, calibration_data):
    """
    Get sensor reading relative to calibrated baseline
    
    Args:
        sensors (dict): Dictionary of sensor objects
        sensor_name (str): Name of sensor ('vl53l0x_0' or 'vl53l0x_1')
        calibration_data (dict): Calibration data
        
    Returns:
        dict: Contains 'raw_mm', 'baseline_mm', 'offset_mm'
    """
    if calibration_data is None:
        raise RuntimeError("No calibration data available. Run calibration first.")
    
    if sensor_name not in calibration_data:
        raise RuntimeError(f"Sensor {sensor_name} not found in calibration data")
    
    raw_reading = get_sensor_value(sensors, sensor_name)
    baseline = calibration_data[sensor_name]['baseline_mm']
    offset = raw_reading - baseline
    
    return {
        'raw_mm': raw_reading,
        'baseline_mm': baseline,
        'offset_mm': offset
    }


def print_calibration_info(calibration_data):
    """Print stored calibration information"""
    if calibration_data is None:
        print("No calibration data available")
        return
    
    print("\n" + "="*50)
    print("CALIBRATION DATA")
    print("="*50)
    
    for sensor_name, data in calibration_data.items():
        print(f"\n{sensor_name.upper()}:")
        print(f"  Baseline: {data['baseline_mm']:.2f} mm")
        print(f"  Timestamp: {time.ctime(data['timestamp'])}")
        if 'samples' in data:
            print(f"  Sample range: {min(data['samples'])} - {max(data['samples'])} mm")
    
    print("\n" + "="*50 + "\n")
