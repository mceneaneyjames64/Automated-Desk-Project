import sys
from hardware import (
	init_i2c, 
	init_mux, 
	scan_i2c_channels,
	init_vl53l0x,
	init_adxl345,
	init_serial,
	get_sensor_value
	)
	
from motor_control import (
	move_station_distance,
	move_station_distance_calibrated,
	move_to_retracted,
	emergency_stop
	)
	
from calibration import (
	calibrate_vl53_sensors, 
	load_calibration, 
	get_calibrated_reading,
	print_calibration_info
	)
	
import config
 
from datetime import datetime, timedelta
import time
import traceback

import os
import csv


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
LOG_FILE = "drift_results.csv"

SEQUENCE = [
    ("out 200",  200),   # extend 200mm from baseline
    ("in 100",   100),   # retract to 100mm from baseline
    ("in 70",     30),   # retract to 30mm from baseline (another 70mm in)
]


def init_all_hardware():
	"""Initialize all hardware components"""
	sensors = {}

	# Initialize I2C and multiplexer
	i2c = init_i2c()
	tca = init_mux(i2c)
	sensors["mux"] = tca

	# Initialize VL53L0X sensors
	sensors["vl53l0x_0"] = init_vl53l0x(tca, config.VL53_CHANNEL_1, "VL53L0X #0") 
	sensors["vl53l0x_1"] = init_vl53l0x(tca, config.VL53_CHANNEL_2, "VL53L0X #1")

	# Initialize ADXL345
	sensors["adxl345"] = init_adxl345(tca)

	print("\n All hardware successfully initialized\n")
	return sensors

# ── Test ──────────────────────────────────────────────────────────────────────

def run_test(sensors, ser, baseline, cycle_number, writer, csv_file, calibration_data):
    print(f"\n{'─'*60}")
    print(f"  Cycle {cycle_number}  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Baseline: {baseline:.1f} mm")
    print(f"{'─'*60}")
    
    print(f"cont mode: {sensors["vl53l0x_0"].is_continuous_mode}")
    temp = sensors["vl53l0x_0"].do_range_measurement()
    print(temp)

    for label, offset in SEQUENCE:

        print(f"\n  → Moving: {label}  (target: {offset:.1f} mm)")
        move_station_distance_calibrated(sensors, calibration_data, "vl53l0x_0", offset, ser)

        sensor_reading = sensors["vl53l0x_0"].range

        # Pause for manual measurement
        manual_input = input(f"  Sensor reads {sensor_reading:.1f} mm. "
                             f"Enter your manual measurement (mm), or press Enter to skip: ").strip()

        manual_mm = None
        if manual_input:
            try:
                manual_mm = float(manual_input)
            except ValueError:
                print("  (invalid input, skipping manual measurement)")

        sensor_error = round(sensor_reading - offset, 2)
        manual_error = round(manual_mm - offset, 2) if manual_mm is not None else ""
        passed = abs(manual_error) <= 3.0

        print(f"  Expected: {offset:.1f} mm  |  "
              f"Sensor: {sensor_reading:.1f} mm (error {sensor_error:+.2f})  |  "
              f"Manual: {manual_mm if manual_mm is not None else '—'} mm"
              + (f" (error {manual_error:+.2f})" if manual_mm is not None else ""))

        row = {
            "timestamp":    datetime.now().isoformat(timespec="seconds"),
            "cycle":        cycle_number,
            "command":      label,
            "expected_mm":  offset,
            "sensor_mm":    sensor_reading,
            "sensor_error": sensor_error,
            "manual_mm":    manual_mm if manual_mm is not None else "",
            "manual_error": manual_error,
            "pass":         "PASS" if passed else "FAIL",
        }
        writer.writerow(row)
        csv_file.flush()

    print(f"\n  ↩  Retracting...")
    move_to_retracted(sensors, "vl53l0x_0", ser)
    print(f"  Done. Actuator retracted.")




def main():
	"""Main program"""
	try:
		# Initialize hardwareThis script initializes various hardware components, including I2C, VL53L0X sensors, and ADXL345, and tests their readings.
		sensors = init_all_hardware()

		# Scan I2C channels
		scan_i2c_channels(sensors["mux"])
		# Initialize serial if needed
		ser = init_serial()

		# Calibrate TOF sensors
		#calibrate_vl53_sensors(sensors)
		calibration_data = calibrate_vl53_sensors(sensors)
		baseline = calibration_data["vl53l0x_0"]["baseline_mm"]
		
		
  
		
		# Set up CSV
		write_header = not os.path.exists(LOG_FILE)
		csv_file = open(LOG_FILE, "a", newline="")
		writer = csv.DictWriter(csv_file, fieldnames=[
			"timestamp", "cycle", "command",
			"expected_mm", "sensor_mm", "sensor_error",
			"manual_mm", "manual_error", "pass",
		])
		
		if write_header:
			writer.writeheader()

		print(f"\nLogging to {LOG_FILE}")
		print("Press Ctrl-C at any time to stop.\n")
		cycle = 1
    
		while True:
			run_test(sensors, ser, baseline, cycle, writer, csv_file, calibration_data)
			cycle += 1
			input("\n  Press Enter to start next cycle, or Ctrl-C to stop...")

    
	except Exception as e:
		print(f"\n Initialization failed: {e}")
		import traceback
		traceback.print_exc()
		return 1
	finally:
		ser.write(config.OFF)
		csv_file.close()
		print(f"Results saved to {LOG_FILE}")
		

if __name__ == '__main__':
	sys.exit(main())
