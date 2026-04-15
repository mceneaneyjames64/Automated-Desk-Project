import importlib
import sys
import threading
import time
import types
from pathlib import Path
from unittest.mock import Mock


class _Message:
    def __init__(self, payload: bytes):
        self.payload = payload


def _load_wrapper_module(move_impl, retract_impl, calibration_impl=None):
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    fake_hardware = types.ModuleType("hardware")
    fake_hardware.init_i2c = lambda: None
    fake_hardware.init_mux = lambda *_: None
    fake_hardware.scan_i2c_channels = lambda *_: None
    fake_hardware.init_vl53l0x = lambda *_: None
    fake_hardware.init_adxl345 = lambda *_: None
    fake_hardware.init_serial = lambda: None
    fake_hardware.get_sensor_value = lambda *_: 0

    fake_motor_control = types.ModuleType("motor_control")
    fake_motor_control.move_to_distance = move_impl
    fake_motor_control.move_to_angle = (
        lambda sensors, target_deg, serial_port, tolerance=1.0, timeout=30:
        move_impl(
            sensors,
            "adxl345",
            target_deg,
            serial_port,
            tolerance=tolerance,
            timeout=timeout,
        )
    )
    fake_motor_control.retract_fully = retract_impl
    fake_motor_control.retract_tilt = (
        lambda sensors, serial_port, timeout=30:
        retract_impl(sensors, "adxl345", serial_port, timeout=timeout)
    )
    fake_motor_control.emergency_stop = Mock()

    fake_calibration = types.ModuleType("calibration")
    if calibration_impl is None:
        calibration_impl = lambda *_: {}
    fake_calibration.calibrate_vl53_sensors = calibration_impl
    fake_calibration.load_calibration = lambda: {}
    fake_calibration.get_calibrated_reading = lambda *_: {"corrected_mm": 0}

    sys.modules["hardware"] = fake_hardware
    sys.modules["motor_control"] = fake_motor_control
    sys.modules["calibration"] = fake_calibration

    if "desk_controller_wrapper" in sys.modules:
        del sys.modules["desk_controller_wrapper"]

    return importlib.import_module("desk_controller_wrapper"), fake_motor_control


def _wait_for(predicate, timeout=2.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_mqtt_motor_command_runs_in_background_and_can_be_stopped():
    started = threading.Event()

    def move_impl(_sensors, _sensor_name, _target_mm, ser, tolerance=2, timeout=30):
        started.set()
        while True:
            ser.write(b"x")
            time.sleep(0.01)

    wrapper_module, motor_control = _load_wrapper_module(
        move_impl=move_impl,
        retract_impl=lambda *_args, **_kwargs: True,
    )

    controller = wrapper_module.DeskControllerWrapper(log_file=None)
    controller.is_initialized = True
    controller.serial_port = Mock()

    started_at = time.time()
    controller._mqtt_on_message(None, None, _Message(b"m1 -> up"))
    assert time.time() - started_at < 0.1
    assert _wait_for(lambda: started.is_set())

    controller._mqtt_on_message(None, None, _Message(b"emergency_stop"))
    assert _wait_for(lambda: controller.motor_status[1] == "stopped")
    motor_control.emergency_stop.assert_called()


def test_only_one_motor_worker_is_started_while_active_move_exists():
    started = threading.Event()
    move_calls = {"count": 0}

    def move_impl(_sensors, _sensor_name, _target_mm, ser, tolerance=2, timeout=30):
        move_calls["count"] += 1
        started.set()
        time.sleep(0.3)
        ser.write(b"x")
        return True

    wrapper_module, _ = _load_wrapper_module(
        move_impl=move_impl,
        retract_impl=lambda *_args, **_kwargs: True,
    )

    controller = wrapper_module.DeskControllerWrapper(log_file=None)
    controller.is_initialized = True
    controller.serial_port = Mock()

    controller._mqtt_on_message(None, None, _Message(b"m1 -> up"))
    assert _wait_for(lambda: started.is_set())

    controller._mqtt_on_message(None, None, _Message(b"m2 -> up"))
    time.sleep(0.1)

    assert move_calls["count"] == 1


def test_mqtt_calibrate_runs_async_and_blocks_motor_movement():
    calibration_started = threading.Event()
    allow_calibration_finish = threading.Event()
    move_calls = {"count": 0}

    def move_impl(_sensors, _sensor_name, _target_mm, _ser, tolerance=2, timeout=30):
        move_calls["count"] += 1
        return True

    def calibration_impl(*_args):
        calibration_started.set()
        allow_calibration_finish.wait(timeout=1.0)
        return {}

    wrapper_module, _ = _load_wrapper_module(
        move_impl=move_impl,
        retract_impl=lambda *_args, **_kwargs: True,
        calibration_impl=calibration_impl,
    )

    controller = wrapper_module.DeskControllerWrapper(log_file=None)
    controller.is_initialized = True
    controller.serial_port = Mock()
    controller.mqtt_connected = True
    controller.mqtt_client = Mock()

    started_at = time.time()
    controller._mqtt_on_message(None, None, _Message(b"calibrate"))
    assert time.time() - started_at < 0.1
    assert _wait_for(lambda: calibration_started.is_set())
    assert _wait_for(lambda: controller.system_state == wrapper_module.SystemState.CALIBRATING)

    controller._mqtt_on_message(None, None, _Message(b"m1 -> up"))

    assert move_calls["count"] == 0
    controller.mqtt_client.publish.assert_any_call("home/desk/status", "calibrating")

    allow_calibration_finish.set()
    assert _wait_for(lambda: controller.system_state == wrapper_module.SystemState.IDLE)
    controller.mqtt_client.publish.assert_any_call("home/desk/status", "Starting calibration")
    controller.mqtt_client.publish.assert_any_call("home/desk/status", "Calibration complete")


def test_direct_motor_methods_reject_while_calibrating():
    move_calls = {"count": 0}
    retract_calls = {"count": 0}

    def move_impl(_sensors, _sensor_name, _target_mm, _ser, tolerance=2, timeout=30):
        move_calls["count"] += 1
        return True

    def retract_impl(_sensors, _sensor_name, _ser, timeout=30):
        retract_calls["count"] += 1
        return True

    wrapper_module, _ = _load_wrapper_module(
        move_impl=move_impl,
        retract_impl=retract_impl,
    )

    controller = wrapper_module.DeskControllerWrapper(log_file=None)
    controller.is_initialized = True
    controller.serial_port = Mock()
    controller.system_state = wrapper_module.SystemState.CALIBRATING

    assert controller.move_motor_to_position(1, 20.0) is False
    assert controller.retract_motor_fully(1) is False
    assert move_calls["count"] == 0
    assert retract_calls["count"] == 0
