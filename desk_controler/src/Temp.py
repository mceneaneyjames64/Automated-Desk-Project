# OLD CODE (run_test based)
from hardware import init_all_hardware, init_serial
from motor_control import move_to_distance, retract_fully
from calibration import calibrate_vl53_sensors
import config
import csv
import os

sensors = init_all_hardware()
ser = init_serial()
calibrate_vl53_sensors(sensors)

SEQUENCE = [
    ("out 200",  200),
    ("in 100",   100),
    ("in 70",     30),
]

def run_test(sensors, ser, cycle_number, writer, csv_file):
    for label, target_mm in SEQUENCE:
        move_to_distance(sensors, config.SENSOR_VL53_0, target_mm, ser)
        # ... manual tracking ...

# Run many cycles
for cycle in range(1, 100):
    run_test(sensors, ser, cycle, writer, csv_file)


# NEW CODE (wrapper based - much simpler!)
from desk_controller_wrapper import DeskControllerWrapper

controller = DeskControllerWrapper()
controller.initialize_hardware()
controller.run_calibration()  # One line instead of separate call

# Simple sequence
sequence = [200, 100, 30]
for position in sequence:
    controller.move_motor_to_position(1, position)
    # Position is automatically tracked
    status = controller.get_system_status()
    print(f"Position: {status['motor_positions'][1]}")

# Done!
controller.shutdown()
