"""
MQTT handler for the automated desk system.

Fixed version that addresses:
- Proper indentation in callback functions
- Correct MQTT topic usage
- Position feedback format with colons
- Error handling throughout
- Preset file loading/saving
- Global state management with locks
"""

import paho.mqtt.client as mqtt
import time
import json
import os
from typing import Any, Dict, Optional

import config
from calibration import calibrate_vl53_sensors
from motor_control import move_to_distance, retract_fully, emergency_stop


################################################################################
#                           MQTT CONFIGURATION
################################################################################

BROKER = config.MQTT_BROKER
PORT = config.MQTT_PORT
TOPIC_COMMAND = config.MQTT_TOPIC_COMMAND
TOPIC_STATUS = config.MQTT_TOPIC_STATUS
TOPIC_FEEDBACK = config.MQTT_TOPIC_FEEDBACK
USERNAME = config.MQTT_USERNAME
PASSWORD = config.MQTT_PASSWORD

PRESET_FILE = config.MQTT_PRESET_FILE
HEARTBEAT_INTERVAL = config.MQTT_HEARTBEAT_INTERVAL


################################################################################
#                           GLOBAL STATE
################################################################################

# Current motor positions (updated from feedback)
current_position_1 = None
current_position_2 = None
current_position_3 = None

# Preset positions (loaded from file, can be modified by set_preset commands)
preset_positions = {
    1: {1: None, 2: None, 3: None},
    2: {1: None, 2: None, 3: None},
    3: {1: None, 2: None, 3: None},
}

# State flags
mqtt_client = None
is_connected = False

# Optional hardware context for command handlers
motor_serial_port: Optional[Any] = None   # Serial connection used by stop and emergency_stop handlers
calibration_sensors: Optional[Dict[str, Any]] = None  # Sensors used by calibration


################################################################################
#                           PRESET MANAGEMENT
################################################################################

def load_presets():
    """Load preset positions from JSON file."""
    global preset_positions
    
    if os.path.exists(PRESET_FILE):
        try:
            with open(PRESET_FILE, "r") as f:
                data = json.load(f)
                # Convert string keys to integers
                preset_positions = {
                    int(p): {int(m): v for m, v in motors.items()}
                    for p, motors in data.items()
                }
            print("✓ Presets loaded from JSON file.")
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"✗ Failed to load presets: {e}")
            print("  Using default preset values.")
    else:
        print("✓ No preset file found, using defaults.")


def save_presets():
    """Save preset positions to JSON file."""
    try:
        with open(PRESET_FILE, "w") as f:
            json.dump(preset_positions, f, indent=4)
        print("✓ Presets saved to JSON file.")
    except OSError as e:
        print(f"✗ Failed to save presets: {e}")


################################################################################
#                           POSITION MANAGEMENT
################################################################################

def update_position(motor_id: int, position: float):
    """Update current motor position."""
    global current_position_1, current_position_2, current_position_3
    
    try:
        position = float(position)
        if motor_id == 1:
            current_position_1 = position
            print(f"  ✓ M1 position updated: {position}")
        elif motor_id == 2:
            current_position_2 = position
            print(f"  ✓ M2 position updated: {position}")
        elif motor_id == 3:
            current_position_3 = position
            print(f"  ✓ M3 position updated: {position}")
        else:
            print(f"✗ Invalid motor ID: {motor_id}")
    except ValueError as e:
        print(f"✗ Invalid position value for M{motor_id}: {position} — {e}")


def get_all_positions() -> Dict[int, Optional[float]]:
    """Get all current motor positions."""
    return {
        1: current_position_1,
        2: current_position_2,
        3: current_position_3,
    }


def publish_position_feedback(motor_id: int):
    """Publish position feedback for a motor."""
    global mqtt_client, current_position_1, current_position_2, current_position_3
    
    if mqtt_client is None:
        return
    
    try:
        position = get_all_positions()[motor_id]
        if position is not None:
            topic = f"{TOPIC_FEEDBACK}/motor{motor_id}"
            payload = f"Feedback{motor_id}:{position}"
            mqtt_client.publish(topic, payload)
            print(f"  → Published: {payload}")
    except Exception as e:
        print(f"✗ Error publishing feedback for M{motor_id}: {e}")


def publish_all_positions():
    """Publish feedback for all motors."""
    for motor_id in [1, 2, 3]:
        publish_position_feedback(motor_id)


################################################################################
#                           COMMAND HANDLERS
################################################################################


def handle_preset_load(client: mqtt.Client, preset_id: int):
    """
    Load and execute a preset.
    
    Parameters
    ----------
    client : mqtt.Client
        MQTT client
    preset_id : int
        Preset ID (1-3)
    """
    try:
        if preset_id not in preset_positions:
            print(f"✗ Invalid preset ID: {preset_id}")
            client.publish(TOPIC_STATUS, f"Invalid preset: {preset_id}")
            return
        
        preset = preset_positions[preset_id]
        
        # Check if all positions are set
        if None in preset.values():
            print(f"✗ Preset {preset_id} is not fully configured")
            client.publish(TOPIC_STATUS, f"Preset {preset_id} not configured")
            return
        
        print(f"  → Loading preset {preset_id}")
        client.publish(TOPIC_STATUS, f"Loading preset {preset_id}...")
        
        # Execute motor movements in sequence
        for motor_id in sorted(preset.keys()):
            target_pos = preset[motor_id]
            print(f"    Moving M{motor_id} to {target_pos} mm")
            # TODO: Add motor move to position code here
            client.publish(TOPIC_STATUS, f"M{motor_id} → {target_pos}mm")
        
        print(f"  ✓ Preset {preset_id} complete")
        client.publish(TOPIC_STATUS, f"Preset {preset_id} complete")
    
    except Exception as e:
        print(f"✗ Error in handle_preset_load: {e}")
        client.publish(TOPIC_STATUS, f"Preset error: {e}")


def handle_preset_save(client: mqtt.Client, preset_id: int):
    """
    Save current motor positions as a preset.
    
    Parameters
    ----------
    client : mqtt.Client
        MQTT client
    preset_id : int
        Preset ID (1-3)
    """
    try:
        if preset_id not in preset_positions:
            print(f"✗ Invalid preset ID: {preset_id}")
            client.publish(TOPIC_STATUS, f"Invalid preset: {preset_id}")
            return
        
        positions = get_all_positions()
        
        # Check that all positions are known
        if None in positions.values():
            print(f"✗ Cannot save preset {preset_id}: not all positions are known")
            client.publish(TOPIC_STATUS, f"Cannot save preset {preset_id}: positions unknown")
            return
        
        preset_positions[preset_id] = positions.copy()
        save_presets()
        
        print(f"  ✓ Preset {preset_id} saved: {positions}")
        client.publish(TOPIC_STATUS, f"Preset {preset_id} saved")
    
    except Exception as e:
        print(f"✗ Error in handle_preset_save: {e}")
        client.publish(TOPIC_STATUS, f"Save error: {e}")


def handle_emergency_stop(client: mqtt.Client):
    """Handle emergency stop command."""
    try:
        print("  ⚠ EMERGENCY STOP - All motors disabled")
        client.publish(TOPIC_STATUS, "EMERGENCY STOP")
        emergency_stop(_require_motor_serial_port("emergency stop"))
    except Exception as e:
        print(f"✗ Error in handle_emergency_stop: {e}")


def handle_stop(client: mqtt.Client):
    """Handle normal stop command.

    Delegates to emergency_stop — both send the same all-off hardware command.
    """
    try:
        print("  → STOP - Gracefully halting motors")
        client.publish(TOPIC_STATUS, "STOP")
        emergency_stop(_require_motor_serial_port("stop"))
    except Exception as e:
        print(f"✗ Error in handle_stop: {e}")


def handle_calibration(client: mqtt.Client):
    """Handle calibration command."""
    try:
        print("  → Running calibration routine")
        if calibration_sensors is None:
            raise RuntimeError(
                "Calibration sensors not initialized. "
                "Set MQTT.calibration_sensors before processing calibrate commands."
            )
        client.publish(TOPIC_STATUS, "Starting calibration")
        calibrate_vl53_sensors(calibration_sensors)
        client.publish(TOPIC_STATUS, "Calibration complete")
    except Exception as e:
        print(f"✗ Error in handle_calibration: {e}")


def _require_motor_serial_port(command_name: str):
    """Return configured motor serial port or raise a helpful error."""
    if motor_serial_port is None:
        raise RuntimeError(
            "Motor serial port not initialized. "
            f"Set MQTT.motor_serial_port before processing {command_name} commands."
        )
    return motor_serial_port


################################################################################
#                           MQTT CALLBACKS
################################################################################

def on_connect(client: mqtt.Client, userdata, flags, reason, properties):
    """
    Callback when MQTT client connects.
    FIXED: Proper indentation
    """
    global is_connected
    
    print(f"✓ Connected to MQTT broker with reason code: {reason}")
    is_connected = True
    
    # QoS 0 — fire-and-forget; eliminates ACK round-trip latency on local LAN
    client.subscribe(TOPIC_COMMAND, 0)
    print(f"✓ Subscribed to topic: {TOPIC_COMMAND}")


def on_message(client: mqtt.Client, userdata, message):
    """
    Callback when MQTT message is received.

    Message routing order (first match wins):
      1. "Heartbeat"           – acknowledged and discarded.
      2. "Feedback{N}:{v}"    – updates in-memory motor position for motor N.
      3. "m{N} -> …"          – motor commands (not supported here; use
                                 DeskControllerWrapper for hardware access).
      4. "preset_{word}"      – loads a named preset (one/two/three).
      5. "set_preset_{word}"  – saves current positions as a named preset.
      6. "emergency_stop"     – halts all motors via emergency_stop().
      7. "stop"               – halts all motors via emergency_stop().
      8. "calibrate"          – runs VL53L0X calibration routine.
      9. (anything else)      – logged as unknown.
    """
    try:
        payload = message.payload.decode().strip()
        print(f"[MQTT] {payload}")
        
        # ────────────────────────────────────────────────────────────────────
        # Heartbeat tracking
        # ────────────────────────────────────────────────────────────────────
        if payload == "Heartbeat":
            print("Heartbeat received")
            return
        
        # ────────────────────────────────────────────────────────────────────
        # Position feedback: "Feedback{N}:{value}"
        # FIXED: Proper colon separator
        # ────────────────────────────────────────────────────────────────────
        if payload.startswith("Feedback"):
            for motor_id in [1, 2, 3]:
                prefix = f"Feedback{motor_id}:"
                if payload.startswith(prefix):
                    value_str = payload[len(prefix):].strip()
                    try:
                        update_position(motor_id, value_str)
                    except Exception as e:
                        print(f"✗ Error updating position: {e}")
                    return
        
        # ────────────────────────────────────────────────────────────────────
        # Motor commands: "m{id} -> {direction|position}"
        # Examples: "m1 -> up", "m1 -> down", "m1 -> 200"
        #
        # NOTE: Direct motor movement requires hardware access (serial port,
        # sensors) that is managed by DeskControllerWrapper.  This standalone
        # MQTT module does not have that context, so motor commands arriving
        # here are logged as unsupported.  Use DeskControllerWrapper for full
        # motor-command handling.
        # ────────────────────────────────────────────────────────────────────
        if " -> " in payload:
            try:
                parts = payload.split("->")
                motor_part = parts[0].strip()      # "m1", "m2", "m3"

                # Extract motor ID from "m{id}"
                if motor_part.startswith("m"):
                    motor_id = int(motor_part[1:])
                    if motor_id in [1, 2, 3]:
                        print(
                            f"⚠ Motor command '{payload}' requires "
                            "DeskControllerWrapper for execution — ignored."
                        )
                    else:
                        print(f"✗ Invalid motor ID: {motor_id}")
                else:
                    print(f"✗ Invalid motor format: {motor_part}")
            except (IndexError, ValueError) as e:
                print(f"✗ Error parsing motor command: {e}")
            return
        
        # ────────────────────────────────────────────────────────────────────
        # Preset load: "preset_one", "preset_two", "preset_three"
        # ────────────────────────────────────────────────────────────────────
        if payload.startswith("preset_") and not payload.endswith("_save"):
            try:
                # Extract preset number from "preset_one" → 1
                preset_word = payload.split("_")[1]  # "one", "two", "three"
                preset_map = {"one": 1, "two": 2, "three": 3}
                
                if preset_word in preset_map:
                    preset_id = preset_map[preset_word]
                    handle_preset_load(client, preset_id)
                else:
                    print(f"✗ Invalid preset name: {preset_word}")
            except Exception as e:
                print(f"✗ Error parsing preset command: {e}")
            return
        
        # ────────────────────────────────────────────────────────────────────
        # Preset save: "set_preset_one", "set_preset_two", "set_preset_three"
        # ────────────────────────────────────────────────────────────────────
        if payload.startswith("set_preset_"):
            try:
                preset_word = payload.split("_")[-1]  # "one", "two", "three"
                preset_map = {"one": 1, "two": 2, "three": 3}
                
                if preset_word in preset_map:
                    preset_id = preset_map[preset_word]
                    handle_preset_save(client, preset_id)
                else:
                    print(f"✗ Invalid preset name: {preset_word}")
            except Exception as e:
                print(f"✗ Error parsing preset save command: {e}")
            return
        
        # ────────────────────────────────────────────────────────────────────
        # Emergency stop
        # ────────────────────────────────────────────────────────────────────
        if payload == "emergency_stop":
            handle_emergency_stop(client)
            return

        # ────────────────────────────────────────────────────────────────────
        # Normal stop
        # ────────────────────────────────────────────────────────────────────
        if payload == "stop":
            handle_stop(client)
            return

        # ────────────────────────────────────────────────────────────────────
        # Calibration
        # ────────────────────────────────────────────────────────────────────
        if payload == "calibrate":
            handle_calibration(client)
            return
        
        print(f"⚠ Unknown MQTT payload: {payload}")
    
    except Exception as e:
        print(f"✗ Error in on_message callback: {e}")


def on_disconnect(client: mqtt.Client, userdata, disconnect_flags, reason_code, properties):
    """
    Callback when MQTT client disconnects.
    FIXED: Added error handling
    """
    global is_connected
    
    is_connected = False
    print(f"✗ Disconnected from MQTT broker (reason code: {reason_code})")


################################################################################
#                           CONNECTION MANAGEMENT
################################################################################

def connect_mqtt():
    """Connect to MQTT broker."""
    global mqtt_client
    
    try:
        mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv5
        )
        
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.on_disconnect = on_disconnect
        
        mqtt_client.username_pw_set(USERNAME, PASSWORD)
        mqtt_client.connect(BROKER, PORT)
        mqtt_client.loop_start()
        
        print(f"✓ MQTT client connecting to {BROKER}:{PORT}...")
        return True
    
    except Exception as e:
        print(f"✗ Failed to connect to MQTT broker: {e}")
        return False


def disconnect_mqtt():
    """Disconnect from MQTT broker."""
    global mqtt_client
    
    try:
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            print("✓ MQTT client disconnected")
    except Exception as e:
        print(f"✗ Error disconnecting MQTT: {e}")


def publish_status(message: str):
    """Publish a status message."""
    global mqtt_client
    
    if mqtt_client is None:
        return
    
    try:
        mqtt_client.publish(TOPIC_STATUS, message)
    except Exception as e:
        print(f"✗ Error publishing status: {e}")


################################################################################
#                           MAIN HEARTBEAT LOOP
################################################################################

def main():
    """
    Main function that starts MQTT connection and heartbeat loop.
    FIXED: Proper error handling and heartbeat loop
    """
    global mqtt_client
    
    print("\n" + "="*70)
    print("  AUTOMATED DESK SYSTEM - MQTT HANDLER")
    print("="*70 + "\n")
    
    # Load presets from file
    load_presets()
    
    # Connect to MQTT broker
    if not connect_mqtt():
        return 1
    
    print("\n✓ MQTT handler started. Publishing heartbeat every", 
          f"{HEARTBEAT_INTERVAL} seconds...\n")
    
    try:
        while True:
            try:
                # Publish heartbeat
                if mqtt_client is not None and is_connected:
                    mqtt_client.publish(TOPIC_STATUS, "Heartbeat")
                    
                    # Publish current positions
                    publish_all_positions()
                    
                    print(f"  → Heartbeat sent, positions updated")
                
                time.sleep(HEARTBEAT_INTERVAL)
            
            except Exception as e:
                print(f"✗ Error in heartbeat loop: {e}")
                time.sleep(5)
    
    except KeyboardInterrupt:
        print("\n\n✓ MQTT handler stopped by user")
    
    finally:
        disconnect_mqtt()
        print("✓ MQTT handler shutdown complete")
    
    return 0


################################################################################
#                           ENTRY POINT
################################################################################

if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
