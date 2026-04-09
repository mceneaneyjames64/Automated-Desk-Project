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
	move_to_distance,
	retract_fully,
	emergency_stop
	)
	
from calibration import (
	calibrate_vl53_sensors,
	load_calibration,
	get_calibrated_reading,
	)
	
import config

from DeskCodeIntegration-UpdatedPositionPublish import preset_positions, payload
 
from datetime import datetime
import time
import traceback

import os
import csv


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
	sensors[config.SENSOR_MUX] = tca

	# Initialize VL53L0X sensors
	sensors[config.SENSOR_VL53_0] = init_vl53l0x(tca, config.VL53_CHANNEL_1, "VL53L0X #0") 
	sensors[config.SENSOR_VL53_1] = init_vl53l0x(tca, config.VL53_CHANNEL_2, "VL53L0X #1")

	# Initialize ADXL345
	sensors[config.SENSOR_ADXL] = init_adxl345(tca)

	print("\n All hardware successfully initialized\n")
	return sensors

def _read_corrected(sensors: dict, sensor_name: str) -> float:
    """
    Return the offset-corrected distance for sensor_name.

    Applies config.OFFSET[sensor_name] to the raw reading.  If no offset is
    present for this sensor (e.g. calibration has not been run yet) the raw
    reading is returned unchanged and a warning is printed once.
    """
    raw = get_sensor_value(sensors, sensor_name)
    offset = getattr(config, "OFFSET", {}).get(sensor_name)
    if offset is None:
        print(f"[motor] Warning: no calibration offset for '{sensor_name}' — "
              f"using raw reading.")
        return raw
    return raw + offset



def run_test(sensors, ser, cycle_number, writer, csv_file):
    print(f"\n{'─'*60}")
    print(f"  Cycle {cycle_number}  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'─'*60}")
    
    for label, target_mm in SEQUENCE:
        print(f"\n  → Moving: {label}  (target: {target_mm} mm)")
        move_to_distance(sensors, config.SENSOR_VL53_0, target_mm, ser)

        sensor_reading = _read_corrected(sensors, config.SENSOR_VL53_0)

        manual_input = input(
            f"  Sensor reads {sensor_reading:.1f} mm. "
            f"Enter your manual measurement (mm), or press Enter to skip: "
        ).strip()

        manual_mm = None
        if manual_input:
            try:
                manual_mm = float(manual_input)
            except ValueError:
                print("  (invalid input, skipping manual measurement)")

        sensor_error = round(sensor_reading - target_mm, 2)
        manual_error = round(manual_mm - target_mm, 2) if manual_mm is not None else ""
        passed = abs(manual_error) <= 3.0 if manual_mm is not None else "N/A"

        print(
            f"  Expected: {target_mm} mm  |  "
            f"Sensor: {sensor_reading:.1f} mm (error {sensor_error:+.2f})  |  "
            f"Manual: {manual_mm if manual_mm is not None else '—'} mm"
            + (f" (error {manual_error:+.2f})" if manual_mm is not None else "")
        )

        row = {
            "timestamp":    datetime.now().isoformat(timespec="seconds"),
            "cycle":        cycle_number,
            "command":      label,
            "expected_mm":  target_mm,
            "sensor_mm":    sensor_reading,
            "sensor_error": sensor_error,
            "manual_mm":    manual_mm if manual_mm is not None else "",
            "manual_error": manual_error,
            "pass":         "PASS" if passed is True else ("FAIL" if passed is False else "N/A"),
        }
        writer.writerow(row)
        csv_file.flush()

    print(f"\n  Retracting...")
    retract_fully(sensors, config.SENSOR_VL53_0, ser)
    print(f"  Done. Actuator retracted.")

def interpret_payload(payload):
	if "monitor_tilt" in payload:
		sens = config.SENSOR_ADX1345
	if "keyboard" in payload:
		sens = config.SENSOR_VL53_0
	if "monitor_up" or "monitor_down" in payload:
		sens = config.SENSOR_VL53_1

	if "preset" in payload:
		if not "set" in payload:
			if "_one" in payload:
				preset = preset_positions[1]
			if "_two" in payload:
				preset = preset_positions[2]
			if "_three" in payload:
				preset = preset_positions[3]
			return preset
		if "set_preset" in paylaod:
			if "one" in payload:
				tilt_reading = _read_corrected(sensors, config.SENSOR_ADX1345)
				montitor_reading = _read_corrected(sensors, config.SENSOR_VL53_1)
				keyboard_reading = _read_corrected(sensors, config.SENSOR_VL53_0)
				preset_positions[1] = {tilt_reading, monitor_reading, keyboard_reading}
			if "two" in payload:
				tilt_reading = _read_corrected(sensors, config.SENSOR_ADX1345)
				montitor_reading = _read_corrected(sensors, config.SENSOR_VL53_1)
				keyboard_reading = _read_corrected(sensors, config.SENSOR_VL53_0)
				preset_positions[2] = {tilt_reading, monitor_reading, keyboard_reading}
			if "three" in payload:
				tilt_reading = _read_corrected(sensors, config.SENSOR_ADX1345)
				montitor_reading = _read_corrected(sensors, config.SENSOR_VL53_1)
				keyboard_reading = _read_corrected(sensors, config.SENSOR_VL53_0)
				preset_positions[3] = {tilt_reading, monitor_reading, keyboard_reading}
			return preset_positions

	if "calibrate" in payload:
		#FIXME: need a way to calibrate the tilt sensor
		calibrate_vl53_sensors(sensors)

	if "emergency_stop" in paylaod:
		emergency_stop(ser)
		
	return sens

def call_preset(preset, payload):
	print(f"\n Moving to {payload}, please wait until movement completed... \n")
	curr = _read_corrected(sensors, sensor_name)
	
	if curr != preset:
		move_to_distance(sensors, config.SENSOR_ADX1345, preset, ser)
		move_to_distance(sensors, config.SENSOR_VL53_0, preset, ser)
		move_to_distance(sensors, config.SENSOR_VL53_1, preset, ser)
		while True:
			curr = _read_corrected(sensors, sensor_name)
			if (curr == preset):
				print(f"\n Moving to {payload} is completed. \n")
				break
	return curr

def increment_move(preset, payload):
	"""Move to current location plus one millimeter
	The plus one below may need to be updated once minimum measurement has been taken"""
	sens = inperpret_payload(payload)
	curr = _read_corrected(sens, sensor_name)
	
	if payload.endswith("_up"):
		updated = curr + 1 
		move_to_distance(sensors, sens, updated, ser)
	if payload.endswith("_down"):
		updated = curr - 1
		move_to_distance(sensors, sens, updated, ser)

def main():
	"""Main program"""
	ser = None
	csv_file = None
	try:
		sensors = init_all_hardware()
		scan_i2c_channels(sensors[config.SENSOR_MUX])
		ser = init_serial()

		calibrate_vl53_sensors(sensors)
		
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
    
		try:
			while True:
				run_test(sensors, ser, cycle, writer, csv_file)
				cycle += 1
				input("\n  Press Enter to start next cycle, or Ctrl-C to stop...")
		except KeyboardInterrupt:
			print("\n\nTest stopped by user.")

	except Exception as e:
		print(f"\nInitialization failed: {e}")
		traceback.print_exc()
		return 1

	finally:
		if ser is not None:
			ser.write(config.CMD_ALL_OFF)
		if csv_file is not None:
			csv_file.close()
			print(f"Results saved to {LOG_FILE}")

	return 0
		

if __name__ == '__main__':
	sys.exit(main())
