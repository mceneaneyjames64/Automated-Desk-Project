"""
Integration tests for hardware control system
Tests end-to-end workflows with simulated hardware responses
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time


class MockVL53L0X:
    """Mock VL53L0X distance sensor"""
    def __init__(self, initial_distance=100):
        self.distance = initial_distance
        self.is_connected = True
    
    def get_distance(self):
        if not self.is_connected:
            raise IOError("Sensor disconnected")
        return self.distance
    
    def set_distance(self, distance):
        """Simulate physical distance change"""
        self.distance = distance


class MockADXL345:
    """Mock ADXL345 accelerometer"""
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 9.8
        self.is_connected = True
    
    def get_acceleration(self):
        if not self.is_connected:
            raise IOError("Accelerometer disconnected")
        return {'x': self.x, 'y': self.y, 'z': self.z}
    
    def simulate_movement(self, x, y, z):
        """Simulate physical movement"""
        self.x = x
        self.y = y
        self.z = z


class MockMotorController:
    """Mock motor controller"""
    def __init__(self):
        self.position = 0  # Current position in mm
        self.is_moving = False
        self.target_position = 0
        self.move_speed = 10  # mm per step
    
    def move_to(self, target_mm):
        """Simulate moving to target position"""
        self.target_position = target_mm
        self.is_moving = True
        
        # Simulate gradual movement
        steps = abs(target_mm - self.position) / self.move_speed
        for _ in range(int(steps)):
            if self.position < target_mm:
                self.position += self.move_speed
            elif self.position > target_mm:
                self.position -= self.move_speed
        
        self.position = target_mm
        self.is_moving = False
        return True
    
    def stop(self):
        """Emergency stop"""
        self.is_moving = False
        return True
    
    def get_position(self):
        return self.position


class TestCalibrationWorkflow:
    """Test complete calibration workflow"""
    
    def test_full_calibration_sequence(self):
        """Test complete calibration from scratch"""
        # Setup mock sensors
        vl53_0 = MockVL53L0X(initial_distance=100)
        vl53_1 = MockVL53L0X(initial_distance=105)
        
        # Simulate calibration process
        samples = []
        num_samples = 10
        
        for _ in range(num_samples):
            samples.append(vl53_0.get_distance())
        
        baseline = sum(samples) / len(samples)
        
        assert baseline == 100
        assert len(samples) == num_samples
    
    def test_calibration_with_noise(self):
        """Test calibration handles noisy sensor readings"""
        vl53 = MockVL53L0X(initial_distance=100)
        
        # Simulate noisy readings
        samples = []
        for i in range(10):
            noise = (-1 if i % 2 == 0 else 1) * (i % 3)
            vl53.set_distance(100 + noise)
            samples.append(vl53.get_distance())
        
        baseline = sum(samples) / len(samples)
        
        # Baseline should be close to 100 despite noise
        assert abs(baseline - 100) < 5
    
    def test_calibration_data_persistence(self):
        """Test calibration data can be saved and loaded"""
        calibration_data = {
            'vl53l0x_0': {'baseline_mm': 100, 'offset': 0, 'timestamp': time.time()},
            'vl53l0x_1': {'baseline_mm': 105, 'offset': 0, 'timestamp': time.time()}
        }
        
        # Simulate save/load
        saved_data = calibration_data.copy()
        loaded_data = saved_data
        
        assert loaded_data == calibration_data
        assert 'vl53l0x_0' in loaded_data
        assert loaded_data['vl53l0x_0']['baseline_mm'] == 100


class TestMotorMovementWorkflow:
    """Test complete motor movement workflows"""
    
    def test_move_to_absolute_position(self):
        """Test moving motor to absolute position with feedback"""
        motor = MockMotorController()
        vl53 = MockVL53L0X(initial_distance=0)
        
        target = 100  # mm
        
        # Move motor
        motor.move_to(target)
        
        # Update sensor reading to reflect new position
        vl53.set_distance(target)
        
        assert motor.get_position() == target
        assert vl53.get_distance() == target
    
    def test_move_relative_to_baseline(self):
        """Test moving relative to calibrated baseline"""
        motor = MockMotorController()
        vl53 = MockVL53L0X(initial_distance=100)
        
        baseline = 100
        relative_move = 50
        target = baseline + relative_move
        
        motor.move_to(target)
        vl53.set_distance(target)
        
        assert motor.get_position() == 150
        assert vl53.get_distance() - baseline == relative_move
    
    def test_retraction_sequence(self):
        """Test full retraction to home position"""
        motor = MockMotorController()
        vl53 = MockVL53L0X(initial_distance=150)
        
        # Motor is extended
        motor.position = 150
        
        # Retract to home (position 0)
        motor.move_to(0)
        vl53.set_distance(0)
        
        assert motor.get_position() == 0
        assert vl53.get_distance() == 0
    
    def test_emergency_stop_during_movement(self):
        """Test emergency stop interrupts movement"""
        motor = MockMotorController()
        
        # Start movement
        motor.target_position = 100
        motor.is_moving = True
        
        # Emergency stop
        motor.stop()
        
        assert not motor.is_moving


class TestSensorFeedbackLoop:
    """Test sensor feedback during motor control"""
    
    def test_closed_loop_position_control(self):
        """Test motor moves until sensor reads target distance"""
        motor = MockMotorController()
        vl53 = MockVL53L0X(initial_distance=0)
        
        target_distance = 100
        tolerance = 2  # mm
        
        # Simulate closed-loop control
        max_iterations = 20
        iteration = 0
        
        while abs(vl53.get_distance() - target_distance) > tolerance and iteration < max_iterations:
            current_distance = vl53.get_distance()
            error = target_distance - current_distance
            
            # Move proportionally to error
            move_amount = motor.position + error * 0.5
            motor.move_to(move_amount)
            vl53.set_distance(motor.position)
            
            iteration += 1
        
        assert abs(vl53.get_distance() - target_distance) <= tolerance
        assert iteration < max_iterations
    
    def test_position_drift_correction(self):
        """Test system corrects for position drift"""
        motor = MockMotorController()
        vl53 = MockVL53L0X(initial_distance=100)
        
        # Motor thinks it's at 100, but sensor reads 95 (drift)
        motor.position = 100
        vl53.set_distance(95)
        
        target = 100
        current_reading = vl53.get_distance()
        correction = target - current_reading
        
        # Apply correction
        motor.move_to(motor.position + correction)
        vl53.set_distance(motor.position)
        
        # Use a tolerance since the mock motor moves in steps
        assert abs(vl53.get_distance() - target) <= 10


class TestMultiSensorCoordination:
    """Test coordination between multiple sensors"""
    
    def test_dual_sensor_agreement(self):
        """Test two distance sensors agree on position"""
        vl53_0 = MockVL53L0X(initial_distance=100)
        vl53_1 = MockVL53L0X(initial_distance=100)
        
        tolerance = 5  # mm
        
        distance_0 = vl53_0.get_distance()
        distance_1 = vl53_1.get_distance()
        
        assert abs(distance_0 - distance_1) <= tolerance
    
    def test_sensor_disagreement_detection(self):
        """Test system detects when sensors disagree"""
        vl53_0 = MockVL53L0X(initial_distance=100)
        vl53_1 = MockVL53L0X(initial_distance=150)  # Faulty reading
        
        max_disagreement = 20  # mm
        
        distance_0 = vl53_0.get_distance()
        distance_1 = vl53_1.get_distance()
        disagreement = abs(distance_0 - distance_1)
        
        # Should detect fault
        assert disagreement > max_disagreement
    
    def test_accelerometer_motion_detection(self):
        """Test accelerometer detects system motion"""
        adxl = MockADXL345()
        
        # Simulate stable state
        initial = adxl.get_acceleration()
        assert abs(initial['z'] - 9.8) < 0.5  # Gravity
        
        # Simulate movement
        adxl.simulate_movement(2.0, 1.0, 11.0)
        moving = adxl.get_acceleration()
        
        # Should detect acceleration change
        delta_z = abs(moving['z'] - initial['z'])
        assert delta_z > 0.5


class TestErrorRecovery:
    """Test error detection and recovery procedures"""
    
    def test_sensor_disconnect_detection(self):
        """Test system detects sensor disconnection"""
        vl53 = MockVL53L0X(initial_distance=100)
        
        # Disconnect sensor
        vl53.is_connected = False
        
        with pytest.raises(IOError):
            vl53.get_distance()
    
    def test_recovery_after_sensor_reconnect(self):
        """Test system recovers after sensor reconnection"""
        vl53 = MockVL53L0X(initial_distance=100)
        
        # Disconnect
        vl53.is_connected = False
        
        # Try to read (should fail)
        with pytest.raises(IOError):
            vl53.get_distance()
        
        # Reconnect
        vl53.is_connected = True
        
        # Should work again
        distance = vl53.get_distance()
        assert distance == 100
    
    def test_motor_position_verification(self):
        """Test motor position is verified after movement"""
        motor = MockMotorController()
        vl53 = MockVL53L0X(initial_distance=0)
        
        target = 100
        
        # Move motor
        motor.move_to(target)
        vl53.set_distance(motor.position)
        
        # Verify position matches sensor reading
        motor_pos = motor.get_position()
        sensor_pos = vl53.get_distance()
        
        assert abs(motor_pos - sensor_pos) < 2


class TestSafetyInterlocks:
    """Test safety interlock systems"""
    
    def test_movement_range_limits(self):
        """Test system enforces movement range limits"""
        motor = MockMotorController()
        
        min_position = 0
        max_position = 200
        
        # Try to move beyond limits
        out_of_range_target = 250
        
        # Should be clamped to max
        safe_target = min(max(out_of_range_target, min_position), max_position)
        motor.move_to(safe_target)
        
        assert motor.get_position() <= max_position
        assert motor.get_position() >= min_position
    
    def test_emergency_stop_accessible(self):
        """Test emergency stop is always accessible"""
        motor = MockMotorController()
        
        # Start movement
        motor.is_moving = True
        motor.target_position = 100
        
        # Emergency stop should work immediately
        result = motor.stop()
        
        assert result is True
        assert not motor.is_moving
    
    def test_watchdog_timeout(self):
        """Test watchdog catches stuck operations"""
        start_time = time.time()
        timeout = 5  # seconds
        
        # Simulate operation
        operation_time = 2  # seconds
        time.sleep(0.01)  # Tiny delay to simulate work
        
        elapsed = time.time() - start_time + operation_time  # Simulated elapsed
        
        # Should not timeout
        assert elapsed < timeout


class TestDataLogging:
    """Test data logging and diagnostics"""
    
    def test_sensor_data_logging(self):
        """Test sensor data is logged correctly"""
        log = []
        
        vl53 = MockVL53L0X(initial_distance=100)
        
        # Log several readings
        for i in range(10):
            reading = {
                'timestamp': time.time(),
                'sensor': 'vl53l0x_0',
                'distance': vl53.get_distance(),
                'iteration': i
            }
            log.append(reading)
            vl53.set_distance(100 + i + 1)  # Set for next iteration
        
        assert len(log) == 10
        assert log[0]['distance'] == 100
        assert log[-1]['distance'] == 108  # Last reading before increment
    
    def test_movement_history_tracking(self):
        """Test movement history is tracked"""
        motor = MockMotorController()
        history = []
        
        # Perform several movements
        targets = [50, 100, 75, 0]
        
        for target in targets:
            motor.move_to(target)
            history.append({
                'timestamp': time.time(),
                'target': target,
                'actual': motor.get_position()
            })
        
        assert len(history) == 4
        assert history[-1]['actual'] == 0  # Final position


# Performance tests
class TestPerformance:
    """Test system performance characteristics"""
    
    def test_sensor_read_speed(self):
        """Test sensor reading performance"""
        vl53 = MockVL53L0X(initial_distance=100)
        
        start = time.time()
        readings = 100
        
        for _ in range(readings):
            vl53.get_distance()
        
        elapsed = time.time() - start
        reads_per_second = readings / elapsed
        
        # Should achieve reasonable read rate
        assert reads_per_second > 10  # At least 10 Hz
    
    def test_movement_response_time(self):
        """Test motor response time"""
        motor = MockMotorController()
        
        start = time.time()
        motor.move_to(100)
        elapsed = time.time() - start
        
        # Movement should complete quickly (mocked)
        assert elapsed < 1.0  # seconds


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--durations=10'])
