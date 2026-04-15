import importlib
import sys
from pathlib import Path


def test_sensor_motor_commands_use_expected_motor_to_sensor_associations():
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
