#!/usr/bin/env python3
"""
Diagnostic script to test motor command flow and identify bottlenecks.
Run this to verify the MQTT→motor command chain is working.
"""

import sys
import time
import threading
from unittest.mock import Mock, MagicMock
from desk_controller_wrapper import DeskControllerWrapper, SystemState

def test_motor_command_flow():
    """Test the complete motor command flow without actual hardware."""
    
    print("=" * 70)
    print("  MOTOR COMMAND FLOW DIAGNOSTIC")
    print("=" * 70)
    
    # Create a mock controller
    controller = DeskControllerWrapper(log_file=None)
    controller.is_initialized = True
    controller.serial_port = Mock()
    controller.mqtt_connected = True
    controller.mqtt_client = Mock()
    
    # Mock the motor control functions to just log calls
    move_calls = []
    def mock_move_to_position(motor_id, target_value):
        move_calls.append(("move", motor_id, target_value))
        print(f"  [MOCK] move_motor_to_position({motor_id}, {target_value})")
        time.sleep(0.5)  # Simulate movement
        return True
    
    # Monkey-patch for testing
    import desk_controller_wrapper
    original_move = desk_controller_wrapper.move_to_distance
    original_angle = desk_controller_wrapper.move_to_angle
    
    desk_controller_wrapper.move_to_distance = lambda *args, **kwargs: True
    desk_controller_wrapper.move_to_angle = lambda *args, **kwargs: True
    
    print("\n1. Testing motor command lock acquisition...")
    print(f"   Initial lock held: {controller.motor_command_lock.locked()}")
    
    print("\n2. Simulating MQTT motor command: 'm1 -> up'")
    print(f"   Motor status before: {controller.motor_status}")
    
    # This simulates what happens when MQTT receives "m1 -> up"
    try:
        # Manually trigger what _mqtt_on_message does
        class FakeMessage:
            def __init__(self, payload):
                self.payload = payload.encode()
        
        message = FakeMessage("m1 -> up")
        controller._mqtt_on_message(None, None, message)
        
        print(f"   Motor status after: {controller.motor_status}")
        print(f"   Lock held after command: {controller.motor_command_lock.locked()}")
        
        # Wait for worker thread to complete
        print("\n3. Waiting for motor worker thread to complete...")
        for i in range(10):
            if not controller.motor_command_lock.locked():
                print(f"   ✓ Lock released after {(i+1)*0.1:.1f}s")
                break
            time.sleep(0.1)
        else:
            print(f"   ✗ Lock still held after 1.0s - DEADLOCK DETECTED!")
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n4. Testing second motor command (should not be rejected)...")
    try:
        message2 = FakeMessage("m2 -> down")
        controller._mqtt_on_message(None, None, message2)
        
        # Give it time to start
        time.sleep(0.2)
        print(f"   Motor 2 status: {controller.motor_status[2]}")
        
        # Wait for completion
        for i in range(10):
            if not controller.motor_command_lock.locked():
                print(f"   ✓ Second command completed")
                break
            time.sleep(0.1)
        else:
            print(f"   ✗ Second command stuck - motors are blocked")
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 70)
    
    # Restore
    desk_controller_wrapper.move_to_distance = original_move
    desk_controller_wrapper.move_to_angle = original_angle

if __name__ == "__main__":
    test_motor_command_flow()
