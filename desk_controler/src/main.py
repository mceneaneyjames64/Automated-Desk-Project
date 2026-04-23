"""
Main entry point for the automated desk system.
Integrates all subsystems through the DeskControllerWrapper.

This replaces the old main.py that used run_test() and provides:
- Hardware initialization
- MQTT integration
- Motor control
- Preset management
- Calibration support
- Interactive command interface
"""

import sys
import time
import signal
from desk_controller_wrapper import DeskControllerWrapper


# Global controller instance for signal handling
controller = None


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n✓ Shutdown requested...")
    if controller:
        controller.shutdown()
    sys.exit(0)


def print_menu():
    """Print available commands."""
    print("\n" + "="*70)
    print("  DESK CONTROLLER - INTERACTIVE MENU")
    print("="*70)
    print("\nMotor Control:")
    print("  1  - Move motor 1 to custom position (mm)")
    print("  2  - Move motor 2 to custom position (mm)")
    print("  3  - Move motor 3 to custom position (mm)")
    print("  4  - Retract motor 1 fully")
    print("  5  - Retract motor 2 fully")
    print("  6  - Retract motor 3 fully")
    print("  7  - Retract ALL motors")
    print()
    print("Preset Control:")
    print("  p1 - Load and execute preset 1")
    print("  p2 - Load and execute preset 2")
    print("  p3 - Load and execute preset 3")
    print("  s1 - Save current position as preset 1")
    print("  s2 - Save current position as preset 2")
    print("  s3 - Save current position as preset 3")
    print()
    print("Maintenance:")
    print("  c  - Run sensor calibration")
    print("  st - Show system status")
    print("  em - EMERGENCY STOP (disable all motors)")
    print()
    print("Application:")
    print("  q  - Quit and shutdown")
    print("="*70)


def get_position_input(motor_id: int) -> float:
    """Get position input from user."""
    while True:
        try:
            position = input(f"\nEnter target position for motor {motor_id} (mm): ").strip()
            value = float(position)
            
            # Validate range
            import config
            if value < config.MIN_POSITION or value > config.MAX_POSITION:
                print(f"✗ Position must be between {config.MIN_POSITION} and {config.MAX_POSITION} mm")
                continue
            
            return value
        except ValueError:
            print("✗ Invalid input. Please enter a number.")


def handle_motor_move(controller: DeskControllerWrapper, motor_id: int):
    """Handle motor movement command."""
    try:
        target_mm = get_position_input(motor_id)
        
        print(f"\n→ Moving motor {motor_id} to {target_mm} mm...")
        if controller.move_motor_to_position(motor_id, target_mm):
            print(f"✓ Motor {motor_id} reached {target_mm} mm")
        else:
            print(f"✗ Motor {motor_id} failed to reach {target_mm} mm")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def handle_motor_retract(controller: DeskControllerWrapper, motor_id: int):
    """Handle motor retraction command."""
    try:
        print(f"\n→ Retracting motor {motor_id}...")
        if controller.retract_motor_fully(motor_id):
            print(f"✓ Motor {motor_id} fully retracted")
        else:
            print(f"✗ Motor {motor_id} failed to retract")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def handle_retract_all(controller: DeskControllerWrapper):
    """Handle retract all motors command."""
    try:
        print("\n→ Retracting ALL motors...")
        all_success = True
        for motor_id in [1, 2, 3]:
            if not controller.retract_motor_fully(motor_id):
                all_success = False
                print(f"✗ Motor {motor_id} failed to retract")
        
        if all_success:
            print("✓ All motors fully retracted")
        else:
            print("⚠ Some motors failed to retract")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def handle_preset_load(controller: DeskControllerWrapper, preset_id: int):
    """Handle preset load command."""
    try:
        preset = controller.presets[preset_id]
        
        # Check if preset is configured
        if None in preset.values():
            print(f"✗ Preset {preset_id} is not configured")
            print(f"  Positions: M1={preset[1]}, M2={preset[2]}, M3={preset[3]}")
            return
        
        print(f"\n→ Loading preset {preset_id}...")
        print(f"  Target positions: M1={preset[1]}mm, M2={preset[2]}mm, M3={preset[3]}mm")
        
        if controller.load_and_execute_preset(preset_id):
            print(f"✓ Preset {preset_id} executed successfully")
        else:
            print(f"✗ Preset {preset_id} execution failed")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def handle_preset_save(controller: DeskControllerWrapper, preset_id: int):
    """Handle preset save command."""
    try:
        print(f"\n→ Saving current position as preset {preset_id}...")
        
        if controller.save_current_position_as_preset(preset_id):
            current_positions = controller.motor_positions
            print(f"✓ Preset {preset_id} saved successfully")
            print(f"  Positions: M1={current_positions[1]}, M2={current_positions[2]}, M3={current_positions[3]}")
        else:
            print(f"✗ Failed to save preset {preset_id}")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def handle_calibration(controller: DeskControllerWrapper):
    """Handle calibration command."""
    try:
        print("\n" + "="*70)
        print("  SENSOR CALIBRATION")
        print("="*70)
        print("\nCalibration will measure sensor accuracy and apply offsets.")
        print("Ensure all motors are FULLY RETRACTED before continuing.\n")
        
        response = input("Continue with calibration? (yes/no): ").strip().lower()
        if response not in ["yes", "y"]:
            print("Calibration cancelled")
            return
        
        if controller.run_calibration():
            print("\n✓ Calibration completed successfully")
        else:
            print("\n✗ Calibration failed")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def handle_emergency_stop(controller: DeskControllerWrapper):
    """Handle emergency stop command."""
    try:
        print("\n" + "="*70)
        print("  EMERGENCY STOP - ALL MOTORS DISABLED")
        print("="*70)
        
        if controller.emergency_stop_all():
            print("✓ All motors have been stopped")
        else:
            print("✗ Error during emergency stop")
    
    except Exception as e:
        print(f"✗ Error: {e}")


def run_interactive_loop(controller: DeskControllerWrapper):
    """
    Run interactive command loop.
    
    Parameters
    ----------
    controller : DeskControllerWrapper
        The desk controller instance
    """
    while True:
        try:
            print_menu()
            command = input("\nEnter command: ").strip().lower()
            
            if command == "1":
                handle_motor_move(controller, 1)
            elif command == "2":
                handle_motor_move(controller, 2)
            elif command == "3":
                handle_motor_move(controller, 3)
            elif command == "4":
                handle_motor_retract(controller, 1)
            elif command == "5":
                handle_motor_retract(controller, 2)
            elif command == "6":
                handle_motor_retract(controller, 3)
            elif command == "7":
                handle_retract_all(controller)
            elif command == "p1":
                handle_preset_load(controller, 1)
            elif command == "p2":
                handle_preset_load(controller, 2)
            elif command == "p3":
                handle_preset_load(controller, 3)
            elif command == "s1":
                handle_preset_save(controller, 1)
            elif command == "s2":
                handle_preset_save(controller, 2)
            elif command == "s3":
                handle_preset_save(controller, 3)
            elif command == "c":
                handle_calibration(controller)
            elif command == "st":
                controller.print_system_status()
            elif command == "em":
                handle_emergency_stop(controller)
            elif command == "q":
                print("\n✓ Quitting application...")
                break
            else:
                print("✗ Unknown command. Please try again.")
        
        except KeyboardInterrupt:
            print("\n\n✓ Quit requested")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main application entry point."""
    global controller
    
    print("\n" + "="*70)
    print("  AUTOMATED DESK SYSTEM - MAIN APPLICATION")
    print("="*70 + "\n")
    
    # Set up signal handling for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create controller instance
    controller = DeskControllerWrapper(
        broker="192.168.1.138",
        mqtt_port=1883,
        mqtt_username="mqtttest",
        mqtt_password="VMIececapstone",
        mqtt_command_topic="home/desk/command",
        mqtt_status_topic="home/desk/status",
        mqtt_feedback_topic="home/desk/feedback",
        presets_file="desk_presets.json",
        log_file="desk_controller.log"
    )
    
    try:
        # ────────────────────────────────────────────────────────────────────
        # 1. Initialize Hardware
        # ────────────────────────────────────────────────────────────────────
        print("[1/4] Initializing hardware...")
        if not controller.initialize_hardware():
            print("✗ Hardware initialization failed")
            return 1
        print("✓ Hardware initialized\n")
        
        # ───────────────────────────────────────────────────────────────────
        # 2. Load Presets
        # ────────────────────────────────────────────────────────────────────
        print("[2/4] Loading presets...")
        controller.load_presets_from_file()
        print("✓ Presets loaded\n")
        
        # ────────────────────────────────────────────────────────────────────
        # 3. Connect to MQTT (optional - can run without it)
        # ────────────────────────────────────────────────────────────────────
        print("[3/4] Connecting to MQTT broker...")
        mqtt_success = controller.mqtt_connect()
        if mqtt_success:
            print("✓ MQTT connected\n")
        else:
            print("⚠ MQTT connection failed - running in standalone mode\n")
        
        # ────────────────────────────────────────────────────────────────────
        # 4. Print System Status and Run Interactive Loop
        # ────────────────────────────────────────────────────────────────────
        print("[4/4] System ready!")
        controller.print_system_status()
        
        # Run interactive command loop
        run_interactive_loop(controller)
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        controller.shutdown()


if __name__ == "__main__":
    sys.exit(main())
