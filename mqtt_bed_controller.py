#!/home/jd/Dev/BedControl/.venv/bin/python

import asyncio
from bleak import BleakClient
from aiomqtt import Client, MqttError

################################################################################
#                           CONFIGURATION & BLE SETUP
################################################################################

BED_ADDRESS = "D0:87:18:BA:53:BC"
WRITE_CHAR_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "0000ffe4-0000-1000-8000-00805f9b34fb"

# Command constants for the bed.
CMD_HEAD_UP = 0x10
CMD_HEAD_DOWN = 0x20
CMD_BACK_TILT_UP = 0x1
CMD_BACK_TILT_DOWN = 0x2
CMD_LEG_UP = 0x4
CMD_LEG_DOWN = 0x8
CMD_SIT = 0x8000
CMD_ZERO_G = 0x1000
CMD_VIBRATE_HEAD = 0x100
CMD_VIBRATE_FEET = 0x400
CMD_FLAT = 0x08000000

################################################################################
#                           BLE UTILITY FUNCTIONS
################################################################################

def calc_checksum(packet: bytearray) -> int:
    total = sum(packet[:-1])
    return (~total) & 0xFF

def build_bed_command(key: int) -> bytes:
    pkt = bytearray(8)
    pkt[0] = 0xE5
    pkt[1] = 0xFE
    pkt[2] = 0x16
    pkt[3] = (key >> 0) & 0xFF
    pkt[4] = (key >> 8) & 0xFF
    pkt[5] = (key >> 16) & 0xFF
    pkt[6] = (key >> 24) & 0xFF
    pkt[7] = calc_checksum(pkt)
    return bytes(pkt)

################################################################################
#                           BED CONTROLLER CLASS
################################################################################

class BedController:
    def __init__(self, address: str, write_char_uuid: str):
        self.address = address
        self.write_char_uuid = write_char_uuid
        self.client = BleakClient(address)
        self.lock = asyncio.Lock()

    async def connect(self):
        if not self.client.is_connected:
            try:
                await self.client.connect()
                print("BLE connected")
            except Exception as e:
                print("BLE connection error:", e)

    async def ensure_connected(self):
        if not self.client.is_connected:
            print("BLE not connected, attempting reconnect...")
            await self.connect()
        return self.client.is_connected

    async def write_command(self, command_key: int):
        if await self.ensure_connected():
            cmd = build_bed_command(command_key)
            async with self.lock:
                try:
                    await self.client.write_gatt_char(self.write_char_uuid, cmd)
                except Exception as e:
                    print("Error writing command:", e)
                    await self.client.disconnect()
                    await self.connect()
        else:
            print("Could not connect to BLE device.")

    async def one_off_command(self, command_key: int):
        await self.write_command(command_key)

    async def continuous_command(self, command_key: int):
        try:
            while True:
                await self.write_command(command_key)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print(f"Continuous command {command_key} cancelled.")
            # Clean exit on cancellation.

# Global controller instance.
bed_controller = BedController(BED_ADDRESS, WRITE_CHAR_UUID)

################################################################################
#                           MOVEMENT FUNCTIONS
################################################################################

# One-shot (tap) functions.
async def head_up():
    print("One-shot: Head Up")
    await bed_controller.one_off_command(CMD_HEAD_UP)

async def head_down():
    print("One-shot: Head Down")
    await bed_controller.one_off_command(CMD_HEAD_DOWN)

async def back_up():
    print("One-shot: Back Up")
    await bed_controller.one_off_command(CMD_BACK_TILT_UP)

async def back_down():
    print("One-shot: Back Down")
    await bed_controller.one_off_command(CMD_BACK_TILT_DOWN)

async def leg_up():
    print("One-shot: Leg Up")
    await bed_controller.one_off_command(CMD_LEG_UP)

async def leg_down():
    print("One-shot: Leg Down")
    await bed_controller.one_off_command(CMD_LEG_DOWN)

async def sit():
    print("Sitting...")
    await bed_controller.one_off_command(CMD_SIT)

async def zero_g():
    print("Zero-G...")
    await bed_controller.one_off_command(CMD_ZERO_G)

async def flat():
    print("Flat...")
    await bed_controller.one_off_command(CMD_FLAT)

async def vibrate_head():
    print("Vibrate Head...")
    await bed_controller.one_off_command(CMD_VIBRATE_HEAD)

async def vibrate_feet():
    print("Vibrate Feet...")
    await bed_controller.one_off_command(CMD_VIBRATE_FEET)

################################################################################
#                   MQTT INTEGRATION & CONTINUOUS TASKS
################################################################################

# MQTT broker settings.
MQTT_BROKER = "192.168.1.138" # Broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "home/bed/command"
MQTT_USERNAME = "mqtttest" #Broker username
MQTT_PASSWORD = "VMIececapstone" #Broker password

# One-shot command mapping.
ONE_SHOT_COMMANDS = {
    "head_up": head_up,
    "head_down": head_down,
    "back_up": back_up,
    "back_down": back_down,
    "leg_up": leg_up,
    "leg_down": leg_down,
    "sit": sit,
    "zero_g": zero_g,
    "flat": flat,
    "vibrate_head": vibrate_head,
    "vibrate_feet": vibrate_feet,
}

# Mapping for continuous (hold) commands.
CONTINUOUS_COMMANDS = {
    "head_up": CMD_HEAD_UP,
    "head_down": CMD_HEAD_DOWN,
    "back_up": CMD_BACK_TILT_UP,
    "back_down": CMD_BACK_TILT_DOWN,
    "leg_up": CMD_LEG_UP,
    "leg_down": CMD_LEG_DOWN,
}

# Dictionary to track active continuous tasks.
# For each command (e.g. "head_up"), we store a dict with keys: 'task' and 'last_update'
continuous_tasks = {}

# Timeout: if no repeated message arrives within this many seconds, cancel the continuous command.
CONTINUOUS_TIMEOUT = 0.3

async def mqtt_command_handler():
    async with Client(MQTT_BROKER, port=MQTT_PORT, username=MQTT_USERNAME, password=MQTT_PASSWORD) as client:
        await client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to MQTT topic: {MQTT_TOPIC}")
        async for message in client.messages:
            payload = message.payload.decode().strip()
            print(f"Received MQTT message: {payload}")

            if payload.startswith("start_"):
                cmd = payload[6:]  # e.g. "head_up"
                if cmd in CONTINUOUS_COMMANDS:
                    now = asyncio.get_event_loop().time()
                    if cmd in continuous_tasks:
                        # Update the last update time.
                        continuous_tasks[cmd]['last_update'] = now
                    else:
                        # Start a new continuous task.
                        task = asyncio.create_task(bed_controller.continuous_command(CONTINUOUS_COMMANDS[cmd]))
                        continuous_tasks[cmd] = {'task': task, 'last_update': now}
                        print(f"Started continuous command: {cmd}")
                else:
                    print(f"Unknown continuous command: {cmd}")

            elif payload in ONE_SHOT_COMMANDS:
                asyncio.create_task(ONE_SHOT_COMMANDS[payload]())
            else:
                print(f"Unknown command received: {payload}")

async def continuous_task_monitor():
    while True:
        now = asyncio.get_event_loop().time()
        to_cancel = []
        for cmd, info in continuous_tasks.items():
            if now - info['last_update'] > CONTINUOUS_TIMEOUT:
                to_cancel.append(cmd)
        for cmd in to_cancel:
            task = continuous_tasks[cmd]['task']
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print(f"Stopped continuous command: {cmd}")
            continuous_tasks.pop(cmd, None)
        await asyncio.sleep(0.1)

async def ble_connection_monitor():
    while True:
        if not bed_controller.client.is_connected:
            print("BLE disconnected, attempting reconnect...")
            await bed_controller.connect()
        await asyncio.sleep(5)

################################################################################
#                           MAIN ENTRY POINT
################################################################################

async def main():
    await bed_controller.connect()
    mqtt_task = asyncio.create_task(mqtt_command_handler())
    monitor_task = asyncio.create_task(ble_connection_monitor())
    continuous_monitor_task = asyncio.create_task(continuous_task_monitor())
    await asyncio.gather(mqtt_task, monitor_task, continuous_monitor_task)

if __name__ == "__main__":
    asyncio.run(main())
