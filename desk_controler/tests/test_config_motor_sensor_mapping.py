import importlib
import sys
from pathlib import Path


def test_sensor_motor_command_mappings():
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    config = importlib.import_module("config")

    assert set(config.SENSOR_MOTOR_COMMANDS) == {
        config.SENSOR_ADXL,
        config.SENSOR_VL53_0,
        config.SENSOR_VL53_1,
    }
    assert config.SENSOR_MOTOR_COMMANDS[config.SENSOR_ADXL] == {
        "extend": config.CMD_M1_EXTEND,
        "retract": config.CMD_M1_RETRACT,
    }
    assert config.SENSOR_MOTOR_COMMANDS[config.SENSOR_VL53_0] == {
        "extend": config.CMD_M2_EXTEND,
        "retract": config.CMD_M2_RETRACT,
    }
    assert config.SENSOR_MOTOR_COMMANDS[config.SENSOR_VL53_1] == {
        "extend": config.CMD_M3_EXTEND,
        "retract": config.CMD_M3_RETRACT,
    }


def test_sensor_channel_assignments():
    """Verify that each sensor constant maps to the correct MUX channel number."""
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    config = importlib.import_module("config")

    # VL53L0X #0 (Motor 2) must be on Channel 0
    assert config.VL53_CHANNEL_0 == 0, (
        f"VL53L0X #0 must be on channel 0; got {config.VL53_CHANNEL_0}"
    )
    # VL53L0X #1 (Motor 3) must be on Channel 1
    assert config.VL53_CHANNEL_1 == 1, (
        f"VL53L0X #1 must be on channel 1; got {config.VL53_CHANNEL_1}"
    )
    # ADXL345 (Motor 1) must be on Channel 2
    assert config.ADXL345_CHANNEL == 2, (
        f"ADXL345 must be on channel 2; got {config.ADXL345_CHANNEL}"
    )
    # Channels must all be distinct
    channels = [config.VL53_CHANNEL_0, config.VL53_CHANNEL_1, config.ADXL345_CHANNEL]
    assert len(channels) == len(set(channels)), (
        f"Sensor channel assignments must be unique; got {channels}"
    )
