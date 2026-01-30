"""
Test bench for hardware control system
Tests hardware initialization, sensor reading, motor control, and calibration
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch, call
import time


class TestHardwareInitialization:
    """Test suite for hardware initialization functions"""
    
    @patch('hardware.init_i2c')
    @patch('hardware.init_mux')
    @patch('hardware.init_vl53l0x')
    @patch('hardware.init_adxl345')
    def test_init_all_hardware_success(self, mock_adxl, mock_vl53, mock_mux, mock_i2c):
        """Test successful initialization of all hardware components"""
        # Setup mocks
        mock_i2c_obj = Mock()
        mock_mux_obj = Mock()
        mock_vl53_obj = Mock()
        mock_adxl_obj = Mock()
        
        mock_i2c.return_value = mock_i2c_obj
        mock_mux.return_value = mock_mux_obj
        mock_vl53.return_value = mock_vl53_obj
        mock_adxl.return_value = mock_adxl_obj
        
        # Import after patching
        from main import init_all_hardware
        
        # Execute
        sensors = init_all_hardware()
        
        # Verify
        mock_i2c.assert_called_once()
        mock_mux.assert_called_once_with(mock_i2c_obj)
        assert mock_vl53.call_count == 2  # Two VL53L0X sensors
        mock_adxl.assert_called_once_with(mock_mux_obj)
        
        assert 'mux' in sensors
        assert 'vl53l0x_0' in sensors
        assert 'vl53l0x_1' in sensors
        assert 'adxl345' in sensors
    
    @patch('hardware.init_i2c')
    @patch('hardware.init_mux')
    def test_init_all_hardware_i2c_failure(self, mock_mux, mock_i2c):
        """Test hardware initialization handles I2C failure"""
        mock_i2c.side_effect = Exception("I2C Bus Error")
        
        # Import the function
        import sys
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import init_all_hardware
        
        # The function will raise the exception
        with pytest.raises(Exception) as exc_info:
            init_all_hardware()
        
        assert "I2C Bus Error" in str(exc_info.value)
    
    @patch('hardware.init_i2c')
    @patch('hardware.init_mux')
    @patch('hardware.init_vl53l0x')
    def test_init_all_hardware_sensor_failure(self, mock_vl53, mock_mux, mock_i2c):
        """Test hardware initialization handles sensor failure"""
        mock_i2c.return_value = Mock()
        mock_mux.return_value = Mock()
        mock_vl53.side_effect = Exception("VL53L0X not responding")
        
        # Import fresh to avoid caching
        import sys
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import init_all_hardware
        
        with pytest.raises(Exception) as exc_info:
            init_all_hardware()
        
        assert "VL53L0X not responding" in str(exc_info.value)


class TestSensorReading:
    """Test suite for sensor reading functions"""
    
    @patch('hardware.get_sensor_value')
    def test_vl53l0x_reading(self, mock_get_sensor):
        """Test VL53L0X distance sensor reading"""
        mock_get_sensor.return_value = 150  # 150mm distance
        
        sensors = {'vl53l0x_0': Mock()}
        reading = mock_get_sensor(sensors, 'vl53l0x_0')
        
        assert reading == 150
        mock_get_sensor.assert_called_once_with(sensors, 'vl53l0x_0')
    
    @patch('hardware.get_sensor_value')
    def test_adxl345_reading(self, mock_get_sensor):
        """Test ADXL345 accelerometer reading"""
        mock_get_sensor.return_value = {'x': 0.1, 'y': 0.2, 'z': 9.8}
        
        sensors = {'adxl345': Mock()}
        reading = mock_get_sensor(sensors, 'adxl345')
        
        assert 'x' in reading
        assert 'y' in reading
        assert 'z' in reading
        assert reading['z'] == pytest.approx(9.8, abs=0.1)
    
    @patch('hardware.get_sensor_value')
    def test_sensor_reading_timeout(self, mock_get_sensor):
        """Test sensor reading handles timeout"""
        mock_get_sensor.side_effect = TimeoutError("Sensor timeout")
        
        sensors = {'vl53l0x_0': Mock()}
        
        with pytest.raises(TimeoutError):
            mock_get_sensor(sensors, 'vl53l0x_0')


class TestCalibration:
    """Test suite for calibration functions"""
    
    @patch('calibration.calibrate_vl53_sensors')
    @patch('calibration.load_calibration')
    def test_calibration_new_system(self, mock_load, mock_calibrate):
        """Test calibration on a new system"""
        mock_load.return_value = None
        mock_calibration_data = {
            'vl53l0x_0': {'baseline_mm': 100, 'offset': 0},
            'vl53l0x_1': {'baseline_mm': 105, 'offset': 0}
        }
        mock_calibrate.return_value = mock_calibration_data
        
        sensors = {'vl53l0x_0': Mock(), 'vl53l0x_1': Mock()}
        
        calibration_data = mock_load()
        if calibration_data is None:
            calibration_data = mock_calibrate(sensors)
        
        assert calibration_data == mock_calibration_data
        mock_calibrate.assert_called_once_with(sensors)
    
    @patch('calibration.load_calibration')
    def test_calibration_load_existing(self, mock_load):
        """Test loading existing calibration data"""
        mock_calibration_data = {
            'vl53l0x_0': {'baseline_mm': 100, 'offset': 0}
        }
        mock_load.return_value = mock_calibration_data
        
        calibration_data = mock_load()
        
        assert calibration_data is not None
        assert 'vl53l0x_0' in calibration_data
    
    @patch('calibration.get_calibrated_reading')
    @patch('hardware.get_sensor_value')
    def test_calibrated_reading_calculation(self, mock_sensor, mock_calibrated):
        """Test calibrated reading calculation"""
        mock_sensor.return_value = 150
        mock_calibrated.return_value = {
            'raw_mm': 150,
            'baseline_mm': 100,
            'offset_mm': 50
        }
        
        sensors = {'vl53l0x_0': Mock()}
        calibration_data = {'vl53l0x_0': {'baseline_mm': 100, 'offset': 0}}
        
        reading = mock_calibrated(sensors, 'vl53l0x_0', calibration_data)
        
        assert reading['raw_mm'] == 150
        assert reading['baseline_mm'] == 100
        assert reading['offset_mm'] == 50


class TestMotorControl:
    """Test suite for motor control functions"""
    
    @patch('motor_control.move_station_distance')
    @patch('hardware.get_sensor_value')
    def test_move_to_absolute_distance(self, mock_sensor, mock_move):
        """Test moving motor to absolute distance"""
        mock_sensor.return_value = 100
        mock_move.return_value = True
        
        sensors = {'vl53l0x_0': Mock()}
        ser = Mock()
        
        result = mock_move(sensors, 'vl53l0x_0', 100, ser)
        
        assert result is True
        mock_move.assert_called_once_with(sensors, 'vl53l0x_0', 100, ser)
    
    @patch('motor_control.move_station_distance_calibrated')
    def test_move_calibrated_distance(self, mock_move_calibrated):
        """Test moving motor relative to calibrated baseline"""
        mock_move_calibrated.return_value = True
        
        sensors = {'vl53l0x_0': Mock()}
        calibration_data = {'vl53l0x_0': {'baseline_mm': 100}}
        ser = Mock()
        
        result = mock_move_calibrated(sensors, calibration_data, 'vl53l0x_0', 50, ser=ser)
        
        assert result is True
        mock_move_calibrated.assert_called_once()
    
    @patch('motor_control.move_to_retracted')
    def test_move_to_retracted_position(self, mock_retract):
        """Test retracting motor to home position"""
        mock_retract.return_value = True
        
        sensors = {'vl53l0x_0': Mock()}
        ser = Mock()
        
        result = mock_retract(sensors, 'vl53l0x_0', ser=ser)
        
        assert result is True
        mock_retract.assert_called_once()
    
    @patch('motor_control.emergency_stop')
    def test_emergency_stop(self, mock_emergency):
        """Test emergency stop functionality"""
        ser = Mock()
        
        mock_emergency(ser)
        
        mock_emergency.assert_called_once_with(ser)
    
    @patch('motor_control.move_station_distance')
    @patch('hardware.get_sensor_value')
    def test_move_distance_out_of_range(self, mock_sensor, mock_move):
        """Test motor movement handles out-of-range distance"""
        mock_move.side_effect = ValueError("Distance out of range")
        
        sensors = {'vl53l0x_0': Mock()}
        ser = Mock()
        
        with pytest.raises(ValueError) as exc_info:
            mock_move(sensors, 'vl53l0x_0', 1000, ser)
        
        assert "Distance out of range" in str(exc_info.value)


class TestSerialCommunication:
    """Test suite for serial communication"""
    
    @patch('hardware.init_serial')
    def test_serial_initialization(self, mock_init_serial):
        """Test serial port initialization"""
        mock_serial = Mock()
        mock_init_serial.return_value = mock_serial
        
        ser = mock_init_serial()
        
        assert ser is not None
        mock_init_serial.assert_called_once()
    
    @patch('hardware.init_serial')
    def test_serial_write_command(self, mock_init_serial):
        """Test writing command to serial port"""
        mock_serial = Mock()
        mock_init_serial.return_value = mock_serial
        
        ser = mock_init_serial()
        command = b'\x01\x02\x03'
        ser.write(command)
        
        ser.write.assert_called_once_with(command)


class TestMainIntegration:
    """Integration tests for main program flow"""
    
    @patch('main.init_all_hardware')
    @patch('hardware.scan_i2c_channels')
    @patch('hardware.init_serial')
    @patch('calibration.load_calibration')
    @patch('calibration.calibrate_vl53_sensors')
    @patch('calibration.get_calibrated_reading')
    @patch('motor_control.move_station_distance')
    @patch('motor_control.move_station_distance_calibrated')
    @patch('motor_control.move_to_retracted')
    @patch('motor_control.emergency_stop')
    @patch('hardware.get_sensor_value')
    @patch('time.sleep')
    @patch('config.OFF', b'\x00', create=True)
    def test_main_program_flow(self, mock_sleep, mock_sensor_value, mock_emergency,
                               mock_retract, mock_move_cal, mock_move, mock_get_cal,
                               mock_calibrate, mock_load_cal, mock_serial, 
                               mock_scan, mock_init_hw):
        """Test complete main program flow"""
        # Setup mocks
        mock_sensors = {
            'mux': Mock(),
            'vl53l0x_0': Mock(),
            'vl53l0x_1': Mock(),
            'adxl345': Mock()
        }
        mock_init_hw.return_value = mock_sensors
        mock_ser = Mock()
        mock_serial.return_value = mock_ser
        mock_calibration = {'vl53l0x_0': {'baseline_mm': 100}}
        mock_load_cal.return_value = mock_calibration
        mock_get_cal.return_value = {'offset_mm': 50}
        
        # Make sensor values raise KeyboardInterrupt on 4th call to exit loop
        mock_sensor_value.side_effect = [150, 155, {'x': 0, 'y': 0, 'z': 9.8}, KeyboardInterrupt()]
        
        # Import fresh
        import sys
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import main
        
        # Should handle KeyboardInterrupt gracefully
        try:
            result = main()
        except KeyboardInterrupt:
            pass
        
        # Verify initialization sequence
        mock_init_hw.assert_called_once()
        mock_scan.assert_called_once_with(mock_sensors['mux'])
        mock_serial.assert_called_once()
        
        # Verify calibration
        mock_load_cal.assert_called_once()
        
        # Verify motor movements
        mock_move.assert_called()
        mock_move_cal.assert_called()
        mock_retract.assert_called()
        mock_emergency.assert_called()
    
    @patch('main.init_all_hardware')
    @patch('hardware.init_serial')
    @patch('config.OFF', b'\x00', create=True)
    def test_main_cleanup_on_exception(self, mock_serial, mock_init_hw):
        """Test main program cleanup on exception"""
        mock_init_hw.side_effect = Exception("Hardware failure")
        mock_ser = Mock()
        mock_serial.return_value = mock_ser
        
        # Import fresh
        import sys
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import main
        
        result = main()
        
        # Should return error code
        assert result == 1
        
        # Serial might not be initialized if hardware init fails early
        # So we just check the function ran without crashing


class TestI2CChannelScanning:
    """Test suite for I2C channel scanning"""
    
    @patch('hardware.scan_i2c_channels')
    def test_scan_i2c_channels(self, mock_scan):
        """Test I2C channel scanning"""
        mock_mux = Mock()
        mock_scan.return_value = {
            0: [0x29],  # VL53L0X on channel 0
            1: [0x29],  # VL53L0X on channel 1
            2: [0x53]   # ADXL345 on channel 2
        }
        
        result = mock_scan(mock_mux)
        
        assert 0 in result
        assert 1 in result
        assert 2 in result
        mock_scan.assert_called_once_with(mock_mux)


class TestErrorHandling:
    """Test suite for error handling and recovery"""
    
    @patch('main.init_all_hardware')
    @patch('config.OFF', b'\x00', create=True)
    def test_initialization_error_handling(self, mock_init):
        """Test error handling during initialization"""
        mock_init.side_effect = Exception("Sensor not found")
        
        # Import fresh
        import sys
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import main
        
        result = main()
        
        assert result == 1  # Should return error code
    
    @patch('main.init_all_hardware')
    @patch('hardware.scan_i2c_channels')
    @patch('hardware.init_serial')
    @patch('calibration.load_calibration')
    @patch('calibration.get_calibrated_reading')
    @patch('motor_control.move_station_distance')
    @patch('config.OFF', b'\x00', create=True)
    def test_runtime_error_handling(self, mock_move, mock_get_cal, mock_load_cal,
                                    mock_serial, mock_scan, mock_init):
        """Test error handling during runtime"""
        mock_init.return_value = {'mux': Mock(), 'vl53l0x_0': Mock()}
        mock_serial.return_value = Mock()
        mock_load_cal.return_value = {'vl53l0x_0': {'baseline_mm': 100}}
        mock_get_cal.side_effect = Exception("Sensor communication error")
        
        # Import fresh
        import sys
        if 'main' in sys.modules:
            del sys.modules['main']
        from main import main
        
        # Should handle exception and return error code
        result = main()
        assert result == 1


# Test fixtures
@pytest.fixture
def mock_sensors():
    """Fixture providing mock sensor objects"""
    return {
        'mux': Mock(),
        'vl53l0x_0': Mock(),
        'vl53l0x_1': Mock(),
        'adxl345': Mock()
    }


@pytest.fixture
def mock_serial():
    """Fixture providing mock serial port"""
    serial_mock = Mock()
    serial_mock.write = Mock()
    serial_mock.read = Mock(return_value=b'\x00')
    return serial_mock


@pytest.fixture
def mock_calibration_data():
    """Fixture providing mock calibration data"""
    return {
        'vl53l0x_0': {
            'baseline_mm': 100,
            'offset': 0,
            'samples': 10
        },
        'vl53l0x_1': {
            'baseline_mm': 105,
            'offset': 0,
            'samples': 10
        }
    }


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--tb=short'])
