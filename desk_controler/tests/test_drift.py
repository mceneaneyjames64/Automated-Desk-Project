"""
Actuator Drift Test — Channel 0
=================================
Calibrates, then runs three moves on vl53l0x_0.
Pauses after each move so you can manually measure before continuing.

Run with: python test_drift.py
"""

import time
import csv
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

LOG_FILE = "drift_results.csv"
SENSOR   = "vl53l0x_0"

# Sequence: (label, offset from baseline in mm)
# Each offset is the absolute distance from the retracted baseline
SEQUENCE = [
    ("out 200",  200),   # extend 200mm from baseline
    ("in 100",   100),   # retract to 100mm from baseline
    ("in 70",     30),   # retract to 30mm from baseline (another 70mm in)
]


# ── Hardware ──────────────────────────────────────────────────────────────────

def setup_hardware():
    from hardware import init_i2c, init_mux, init_vl53l0x, init_serial
    import config
    i2c = init_i2c()
    tca = init_mux(i2c)
    sensors = {
        "vl53l0x_0": init_vl53l0x(tca, config.VL53_CHANNEL_0, "VL53L0X #1"),
        "mux": tca,
    }
    ser = init_serial()
    return sensors, ser


def read_sensor(sensors):
    from hardware import get_sensor_value
    return get_sensor_value(sensors, SENSOR)


def move_to(sensors, ser, target_mm):
    from motor_control import move_station_distance
    move_station_distance(sensors, SENSOR, int(target_mm), ser)


def retract(sensors, ser):
    from motor_control import move_to_retracted
    move_to_retracted(sensors, SENSOR, ser=ser)


def stop_all(ser):
    import config
    ser.write(config.OFF)


# ── Test ──────────────────────────────────────────────────────────────────────

def run_test(sensors, ser, baseline, cycle_number, writer, csv_file):
    print(f"\n{'─'*60}")
    print(f"  Cycle {cycle_number}  —  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Baseline: {baseline:.1f} mm")
    print(f"{'─'*60}")

    for label, offset in SEQUENCE:
        expected_mm = baseline + offset

        print(f"\n  → Moving: {label}  (target: {expected_mm:.1f} mm)")
        move_to(sensors, ser, expected_mm)

        sensor_reading = read_sensor(sensors)

        # Pause for manual measurement
        manual_input = input(f"  Sensor reads {sensor_reading:.1f} mm. "
                             f"Enter your manual measurement (mm), or press Enter to skip: ").strip()

        manual_mm = None
        if manual_input:
            try:
                manual_mm = float(manual_input)
            except ValueError:
                print("  (invalid input, skipping manual measurement)")

        sensor_error = round(sensor_reading - expected_mm, 2)
        manual_error = round(manual_mm - expected_mm, 2) if manual_mm is not None else ""
        passed = abs(sensor_error) <= 3.0

        print(f"  Expected: {expected_mm:.1f} mm  |  "
              f"Sensor: {sensor_reading:.1f} mm (error {sensor_error:+.2f})  |  "
              f"Manual: {manual_mm if manual_mm is not None else '—'} mm"
              + (f" (error {manual_error:+.2f})" if manual_mm is not None else ""))

        row = {
            "timestamp":    datetime.now().isoformat(timespec="seconds"),
            "cycle":        cycle_number,
            "command":      label,
            "expected_mm":  expected_mm,
            "sensor_mm":    sensor_reading,
            "sensor_error": sensor_error,
            "manual_mm":    manual_mm if manual_mm is not None else "",
            "manual_error": manual_error,
            "pass":         "PASS" if passed else "FAIL",
        }
        writer.writerow(row)
        csv_file.flush()

    print(f"\n  ↩  Retracting...")
    retract(sensors, ser)
    print(f"  Done. Actuator retracted.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    sensors, ser = setup_hardware()

    # Always run a fresh calibration
    from calibration import calibrate_vl53_sensors
    print("\nRunning calibration — ensure actuator is fully retracted.")
    calibration_data = calibrate_vl53_sensors(sensors)
    baseline = calibration_data[SENSOR]["baseline_mm"]
    print(f"Baseline set: {baseline:.1f} mm")

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
    try:
        while True:
            run_test(sensors, ser, baseline, cycle, writer, csv_file)
            cycle += 1
            input("\n  Press Enter to start next cycle, or Ctrl-C to stop...")

    except KeyboardInterrupt:
        print("\n\nTest stopped.")
    finally:
        stop_all(ser)
        csv_file.close()
        print(f"Results saved to {LOG_FILE}")


if __name__ == "__main__":
    main()
