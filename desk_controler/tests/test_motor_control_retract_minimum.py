import importlib
import sys
import types
from pathlib import Path


class _SerialStub:
    def __init__(self):
        self.writes = []

    def write(self, value):
        self.writes.append(value)


def _load_motor_control():
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    fake_hardware = types.ModuleType("hardware")
    fake_hardware.get_sensor_value = lambda *_: 0.0
    sys.modules["hardware"] = fake_hardware

    if "motor_control" in sys.modules:
        del sys.modules["motor_control"]

    return importlib.import_module("motor_control")


def test_retract_fully_uses_raw_sensor_value_for_minimum_check():
    motor_control = _load_motor_control()
    serial_stub = _SerialStub()

    motor_control.get_sensor_value = lambda *_: motor_control.config.MIN_POSITION
    motor_control._read_corrected = lambda *_: motor_control.config.MIN_POSITION + 50

    result = motor_control.retract_fully(
        sensors={},
        sensor_name=motor_control.config.SENSOR_VL53_0,
        ser=serial_stub,
        timeout=0.2,
    )

    assert result is True
    assert serial_stub.writes == [motor_control.config.CMD_ALL_OFF]
