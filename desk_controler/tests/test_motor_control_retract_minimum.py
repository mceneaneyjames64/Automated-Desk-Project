import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch


class _SerialStub:
    def __init__(self):
        self.writes = []

    def write(self, value):
        self.writes.append(value)


def _load_motor_control():
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    def _require_explicit_patch(*_args, **_kwargs):
        raise AssertionError("Test must patch motor_control.get_sensor_value explicitly.")

    fake_hardware = types.ModuleType("hardware")
    fake_hardware.get_sensor_value = _require_explicit_patch
    sys.modules["hardware"] = fake_hardware

    if "motor_control" in sys.modules:
        del sys.modules["motor_control"]

    return importlib.import_module("motor_control")


def test_retract_fully_stops_at_raw_minimum():
    motor_control = _load_motor_control()
    serial_stub = _SerialStub()
    mock_sensor = object()

    with patch.object(
        motor_control, "get_sensor_value", return_value=motor_control.config.MIN_POSITION
    ), patch.object(
        motor_control,
        "_read_corrected",
        return_value=motor_control.config.MIN_POSITION + 50,
    ):
        result = motor_control.retract_fully(
            sensors={motor_control.config.SENSOR_VL53_0: mock_sensor},
            sensor_name=motor_control.config.SENSOR_VL53_0,
            ser=serial_stub,
            timeout=0.2,
        )

    assert result is True
    assert serial_stub.writes == [motor_control.config.CMD_ALL_OFF]
