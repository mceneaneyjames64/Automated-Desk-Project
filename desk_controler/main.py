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
 
import time


def init_all_hardware():
	"""Initialize all hardware components"""
	sensors = {}

	# Initialize I2C and multiplexer
	i2c = init_i2c()
	tca = init_mux(i2c)
	sensors["mux"] = tca

	# Initialize VL53L0X sensors
	sensors["vl53l0x_0"] = init_vl53l0x(tca, config.VL53_CHANNEL_1, "VL53L0X #1") 
	sensors["vl53l0x_1"] = init_vl53l0x(tca, config.VL53_CHANNEL_2, "VL53L0X #2")

	# Initialize ADXL345
	sensors["adxl345"] = init_adxl345(tca)

	print("\n All hardware successfully initialized\n")
	return sensors
 
def main():
	"""Main program"""
	try:
		# Initialize hardwareThis script initializes various hardware components, including I2C, VL53L0X sensors, and ADXL345, and tests their readings.
		sensors = init_all_hardware()

		# Scan I2C channels
		scan_i2c_channels(sensors["mux"])

		# Initialize serial if needed
		ser = init_serial()

		print("\n System ready \n Begining calibration")
		
		# Option 2: Load existing calibration
		calibration_data = load_calibration()
		if calibration_data is None:
			calibration_data = calibrate_vl53_sensors(sensors)
    
		# Use calibrated readings
		reading = get_calibrated_reading(sensors, 'vl53l0x_0', calibration_data)
		print(f"Offset from baseline: {reading['offset_mm']:.2f} mm")

    
		# Move to absolute distance
		move_station_distance(sensors, 'vl53l0x_0', 100, ser)  # Move to 100mm
    
		# Move relative to calibrated baseline
		move_station_distance_calibrated(sensors, calibration_data, 'vl53l0x_0', 50, ser=ser)  # Extend 50mm from baseline
    
		# Retract fully
		move_to_retracted(sensors, 'vl53l0x_0', ser=ser)
    
		# Emergency stop
		emergency_stop(ser) 
		
		while True:

			print(get_sensor_value(sensors, 'vl53l0x_0'))
			print(get_sensor_value(sensors, 'vl53l0x_1'))
			print(get_sensor_value(sensors, 'adxl345'))
						
				

			

			time.sleep(10)

		return 0

	except Exception as e:
		print(f"\n Initialization failed: {e}")
		import traceback
		traceback.print_exc()
		return 1
	finally:
		ser.write(config.OFF)



if __name__ == '__main__':
	sys.exit(main())
