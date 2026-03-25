try:
		start = datetime.now()
		TOF0_sum = start
		TOF1_sum = start
		ACC_sum = start
		
		for i in range (10000):
			print(f"Interation {i}")
			
			# Measaure latency of TOF 0
			s = datetime.now()	# get start time

			temp = get_sensor_value(sensors, 'vl53l0x_0')	# read sensor
		
			e = datetime.now()	# get end time
			elapsed = (e - s).total_seconds()
			td = timedelta(seconds=elapsed)

			print(f"read vl53l0x_0 in {td} seconds")
			TOF0_sum += td
			
			# Measaure latency of TOF 1
			s = datetime.now()	# get start time

			temp = get_sensor_value(sensors, 'vl53l0x_1')	# read sensor
		
			e = datetime.now()	# get end time
			elapsed = (e - s).total_seconds()
			td = timedelta(seconds=elapsed)

			print(f"read vl53l0x_1 in {td} seconds")
			TOF1_sum += td
			
			# Measaure latency of Acc
			s = datetime.now()	# get start time

			temp = get_sensor_value(sensors, 'adxl345')	# read sensor
		
			e = datetime.now()	# get end time
			elapsed = (e - s).total_seconds()
			td = timedelta(seconds=elapsed)

			print(f"read adxl345 in {td} seconds")
			ACC_sum += td
			
		TOF0_avg = (TOF0_sum - start) / 10000
		TOF1_avg = (TOF1_sum - start) / 10000
		ACC_avg  = (ACC_sum - start)  / 10000
		end = datetime.now()
		test_time = (end - start).total_seconds()
		tt = timedelta(seconds=test_time)
		
		print(f" Average latency of Vl53L0X_0: {TOF0_avg} seconds, after 100 interations")
		print(f" Average latency of Vl53L0X_1: {TOF1_avg} seconds, after 100 interations")
		print(f" Average latency of ADXL345: {ACC_avg} seconds, after 100 interations")
		print(f"Test Complete. Elsapsed time: {tt}")
		
	except Exception as e:
		print(f"\nSensor read failed: {e}")
		traceback.print_exc()
		        
	finally:
		print(f"Test ended at time: {datetime.now()}")
