#!/home/jd/Dev/DeskControl/.venv/bin/python

import asyncio
#import paho.mqtt.client as paho
from aiomqtt import Client, MqttError

pending_acks = {}

# MQTT broker settings.
MQTT_BROKER = "192.168.1.138" # Broker IP
MQTT_PORT = 1883
CMD_TOPIC = "home/desk/command"
STATUS_TOPIC = "home/desk/status"
SERVER_STATUS_TOPIC = "home/server/status"
MQTT_USERNAME = "eceMos" # Broker username
MQTT_PASSWORD = "eceMos1" # Broker password

# Latest live raw actuator positions
current_positions = {
    1: None,
    2: None,
    3: None,
}

# Latest live position feedback as percentages for Home Assistant display
current_position_percents = {
    1: None,
    2: None,
    3: None,
}
    
################################################################################
#                       MQTT POSITION PUBLISHING
################################################################################
async def safe_publish(client, topic, payload, retain=False):
    try:
        # Centralized MQTT publish wrapper so network/broker errors
        # do not unexpectedly kill background tasks.
        await client.publish(topic, payload, retain=retain)
        return True
    except asyncio.CancelledError:
        # Always re-raise cancellations so asyncio can shut down cleanly.
        raise
    except MqttError as e:
        print(f"MQTT publish failed on topic '{topic}' with payload '{payload}': {e}")
        return False
    except Exception as e:
        print(f"Unexpected publish error on topic '{topic}': {e}")
        return False

# Function to publish numeric actuator positions as well as percentage values for HA display
async def publish_position(client, actuator_id, raw_value):
    try:
        # Convert incoming feedback text to a numeric value.
        # Save the raw actuator value for preset storage and movement.
        value = float(raw_value)
        percent = value #round(normalize_to_percent(value), 1)

        # Store raw actuator position for preset saving / movement commands
        current_positions[actuator_id] = value

        # Store percentage separately for Home Assistant display
        current_position_percents[actuator_id] = percent

        
    except ValueError:
        print(f"Invalid position value for actuator {actuator_id}: {raw_value}")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Unexpected error in publish_position for actuator {actuator_id}: {e}")


################################################################################
#                           CONFIGURATION
################################################################################

# Command constants for the desk.
CMD_monitor_up = 0x1
CMD_monitor_down = 0x2
CMD_keyboard_up = 0x3
CMD_keyboard_down = 0x4
CMD_monitor_tilt_up = 0x5
CMD_monitor_tilt_down = 0x6
CMD_preset_one = 0x7
CMD_preset_two = 0x8
CMD_preset_three = 0x9
CMD_set_preset_one = 0xa
CMD_set_preset_two = 0xb
CMD_set_preset_three = 0xc
CMD_calibrate = 0xd
CMD_emergency_stop = 0xe

################################################################################
#                           MOVEMENT FUNCTIONS
################################################################################

# One-shot (tap) functions.
async def monitor_up(client):
    print("One-shot: Monitor Up")

async def monitor_down(client):
    print("One-shot: Monitor Down")

async def keyboard_up(client):
    print("One-shot: Keyboard Up")

async def keyboard_down(client):
    print("One-shot: Keyboard Down")

async def monitor_tilt_up(client):
    print("One-shot: Monitor Tilt Up")

async def monitor_tilt_down(client):
    print("One-shot: Monitor Tilt Down")
    
async def calibrate(client):
    print("Calibrate...")

async def emergency_stop(client):
    print("Emergency Stop...")

# Run regular movement with delay for continuous command
async def continuous_command(command_key: int):
        #up/down button on remote function
    try:
        while True:
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        print(f"Continuous command {command_key} cancelled.")
        # Clean exit on cancellation
        raise
    except Exception as e:
            # Catch unexpected task failures so they are visible in testing.
        print(f"Unexpected error in continuous_command {command_key}: {e}")
        raise

################################################################################
#                   MQTT INTEGRATION & CONTINUOUS TASKS
################################################################################



# One-shot command mapping.
ONE_SHOT_COMMANDS = {
    "monitor_up": monitor_up,
    "monitor_down": monitor_down,
    "keyboard_up": keyboard_up,
    "keyboard_down": keyboard_down,
    "monitor_tilt_up": monitor_tilt_up,
    "monitor_tilt_down": monitor_tilt_down,
    "calibrate": calibrate,
    "emergency_stop": emergency_stop,
}

# Mapping for continuous (hold) commands
CONTINUOUS_COMMANDS = {
    "monitor_up": CMD_monitor_up,
    "monitor_down": CMD_monitor_down,
    "keyboard_up": CMD_keyboard_up,
    "keyboard_down": CMD_keyboard_down,
    "monitor_tilt_up": CMD_monitor_tilt_up,
    "monitor_tilt_down": CMD_monitor_tilt_down,
}

continuous_tasks = {}
CONTINUOUS_TIMEOUT = 0.3
HEARTBEAT_TIMEOUT = 120.0

# Global variable to track last heartbeat
last_heartbeat_time = None

async def run_one_shot_command(command_name, client):
    try:
        # Wrap one-shot tasks created with asyncio.create_task()
        # so failures do not become unhandled background exceptions.
        await ONE_SHOT_COMMANDS[command_name](client)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"One-shot command '{command_name}' failed: {e}")

async def mqtt_command_handler(client):
    global last_heartbeat_time

    try:
        # Subscribe inside a protected block so main() can reconnect
        # if the broker is unavailable or disconnects.
        await client.subscribe(CMD_TOPIC)
        print(f"Subscribed to command MQTT topic: {CMD_TOPIC}")
        
        await client.subscribe(STATUS_TOPIC)
        print(f"Subscribed to status MQTT topic: {STATUS_TOPIC}")
        
        await client.subscribe(SERVER_STATUS_TOPIC)
        print(f"Subscribed to upstream status topic: {SERVER_STATUS_TOPIC}")

        async for message in client.messages:
            try:
                # Handle each message inside its own try block.
                # This prevents one bad payload from killing the whole loop.
                
                # Only check topics that are incomeing
                if message.topic:
                    payload = message.payload.decode().strip()
                    print(f"Received MQTT message: {payload}")

                    # Track heartbeat
                    if payload == "service_running":
                        last_heartbeat_time = asyncio.get_running_loop().time()
                        print(f"Recived heartbeat")
                        continue  # Do not treat heartbeats as commands
                        
                    # Detect actuator confirmation
                    if payload in pending_acks:
                        pending_acks[payload].set()
                        continue

                    # Continuous commands
                    if payload.startswith("start_"):
                        cmd = payload[6:]
                        if cmd in CONTINUOUS_COMMANDS:
                            now = asyncio.get_running_loop().time()
                            if cmd in continuous_tasks:
                                continuous_tasks[cmd]['last_update'] = now
                            else:
                                task = asyncio.create_task(
                                    continuous_command(CONTINUOUS_COMMANDS[cmd])
                                )
                                continuous_tasks[cmd] = {'task': task, 'last_update': now}
                                print(f"Started continuous command: {cmd}")
                        else:
                            print(f"Unknown continuous command: {cmd}")

                    # One-shot commands
                    elif payload in ONE_SHOT_COMMANDS:
                        asyncio.create_task(run_one_shot_command(payload, client))

                    else:
                        print(f"Unknown MQTT payload: {payload}")

            except UnicodeDecodeError as e:
                print(f"Failed to decode MQTT payload: {e}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"Error while processing MQTT message: {e}")

    except asyncio.CancelledError:
        raise
    except MqttError as e:
        # Re-raise connection-level MQTT errors so main() can restart cleanly.
        print(f"MQTT command handler connection error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error in mqtt_command_handler: {e}")
        raise

# Check continuous command timeouts.
async def continuous_task_monitor():
    try:
        while True:
            now = asyncio.get_running_loop().time()
            to_cancel = []

            for cmd, info in list(continuous_tasks.items()):
                if now - info['last_update'] > CONTINUOUS_TIMEOUT:
                    to_cancel.append(cmd)

            for cmd in to_cancel:
                task = continuous_tasks[cmd]['task']
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    print(f"Stopped continuous command: {cmd}")
                finally:
                    # Always remove expired task entries,
                    # even if task cancellation raises.
                    continuous_tasks.pop(cmd, None)

            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Unexpected error in continuous_task_monitor: {e}")
        raise


# Monitor heartbeats
async def heartbeat_monitor(client):
    global last_heartbeat_time

    # Tracks whether Home Assistant is currently in a lost-heartbeat state
    # so the code only publishes state changes when needed.
    heartbeat_lost = False

    # Used to detect the startup case where the script never receives
    # an initial heartbeat at all.
    start_time = asyncio.get_running_loop().time()

    try:
        while True:
            now = asyncio.get_running_loop().time()

            # Never received a heartbeat yet
            if last_heartbeat_time is None:
                if now - start_time > HEARTBEAT_TIMEOUT:
                    if not heartbeat_lost:
                        print("ERROR: No heartbeat ever received!")
                        await safe_publish(client, "home/server/status", "lost", retain=True)
                        heartbeat_lost = True
                await asyncio.sleep(1)
                continue

            # Heartbeat was received before, but now timed out
            if now - last_heartbeat_time > HEARTBEAT_TIMEOUT:
                print("ERROR: No heartbeat received!")
                await safe_publish(client, "home/server/status", "lost", retain=True)
                heartbeat_lost = True
            else:
                # If heartbeat recovers after being lost, publish "ok" once
                # so Home Assistant can clear the warning condition.
                print("Heartbeat restored")
                await safe_publish(client, "home/server/status", "ok", retain=True)
                heartbeat_lost = False

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Unexpected error in heartbeat_monitor: {e}")
        raise
        
# Send preset and wait
async def send_and_wait(client, command_payload: str, expected_ack: str, timeout=10, retries=3):
    for attempt in range(1, retries + 1):
        print(f"Sending: {command_payload} (attempt {attempt}/{retries})")
    
        # Create event for this specific ack
        event = asyncio.Event()
        pending_acks[expected_ack] = event

        try:
            # Publish and wait inside the retry loop so every attempt
            # is a real resend attempt.
            await client.publish(CMD_TOPIC, command_payload)

            await asyncio.wait_for(event.wait(), timeout)
            print(f"Ack received: {expected_ack}")
            return True

        except asyncio.TimeoutError:
            print(f"Timeout waiting for ack: {expected_ack}")

        except asyncio.CancelledError:
            raise

        except MqttError as e:
            print(f"MQTT error while sending '{command_payload}': {e}")

        except Exception as e:
            print(f"Unexpected error in send_and_wait for '{command_payload}': {e}")

        finally:
            # Always remove the pending ack for this attempt
            # so stale events do not remain in the dictionary.
            pending_acks.pop(expected_ack, None)
        
    print(f"FAILED after {retries} attempts: {command_payload}")
    return False

################################################################################
#                           MAIN ENTRY POINT
################################################################################

async def main():
    
    while True:
        try:
            # Reconnect loop so the service can recover if the broker disconnects
            # or if one of the long-running tasks exits with an MQTT-related failure.
            async with Client(MQTT_BROKER, port=MQTT_PORT, username=MQTT_USERNAME, password=MQTT_PASSWORD) as client:
                mqtt_task = asyncio.create_task(mqtt_command_handler(client))
                continuous_monitor_task = asyncio.create_task(continuous_task_monitor())
                heartbeat_monitor_task = asyncio.create_task(heartbeat_monitor(client))
            
                await asyncio.gather(mqtt_task, continuous_monitor_task, heartbeat_monitor_task)

        except asyncio.CancelledError:
            raise
        except MqttError as e:
            print(f"MQTT connection failed: {e}")
            print("Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error in main: {e}")
            print("Retrying in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
