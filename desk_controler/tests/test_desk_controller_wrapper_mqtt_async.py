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
        if not allow_calibration_finish.wait(timeout=2.0):
            raise TimeoutError("Calibration test synchronization timed out")
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


def test_preset_load_motors_move_in_correct_order():
    """Motors must be moved in order: M2 (keyboard) → M3 (monitor) → M1 (tilt)."""
    move_order = []

    def move_impl(_sensors, sensor_name, _target, _ser, tolerance=2, timeout=30):
        move_order.append(sensor_name)
        return True

    wrapper_module, _ = _load_wrapper_module(
        move_impl=move_impl,
        retract_impl=lambda *_args, **_kwargs: True,
    )

    controller = wrapper_module.DeskControllerWrapper(log_file=None)
    controller.is_initialized = True
    controller.serial_port = Mock()
    controller.presets[1] = {1: 90.0, 2: 200.0, 3: 300.0}

    result = controller.load_and_execute_preset(1)

    assert result is True
    # M2 uses vl53l0x_0, M3 uses vl53l0x_1, M1 uses adxl345
    assert move_order == ["vl53l0x_0", "vl53l0x_1", "adxl345"]


def test_preset_load_mqtt_message_numeric_format():
    """MQTT 'preset 1' message triggers preset execution."""
    preset_executed = threading.Event()

    def move_impl(_sensors, _sensor_name, _target, _ser, tolerance=2, timeout=30):
        preset_executed.set()
        return True

    wrapper_module, _ = _load_wrapper_module(
        move_impl=move_impl,
        retract_impl=lambda *_args, **_kwargs: True,
    )

    controller = wrapper_module.DeskControllerWrapper(log_file=None)
    controller.is_initialized = True
    controller.serial_port = Mock()
    controller.presets[2] = {1: 90.0, 2: 150.0, 3: 250.0}

    controller._mqtt_on_message(None, None, _Message(b"preset 2"))
    assert _wait_for(lambda: preset_executed.is_set())


def test_save_preset_mqtt_message_numeric_format(tmp_path):
    """MQTT 'save preset 1' message saves current positions to preset."""
    wrapper_module, _ = _load_wrapper_module(
        move_impl=lambda *_args, **_kwargs: True,
        retract_impl=lambda *_args, **_kwargs: True,
    )

    presets_file = str(tmp_path / "test_presets.json")
    controller = wrapper_module.DeskControllerWrapper(
        presets_file=presets_file,
        log_file=None,
    )
    controller.is_initialized = True
    controller.serial_port = Mock()
    controller.motor_positions = {1: 80.0, 2: 180.0, 3: 280.0}

    controller._mqtt_on_message(None, None, _Message(b"save preset 3"))

    assert controller.presets[3] == {1: 80.0, 2: 180.0, 3: 280.0}


def test_preset_load_emergency_stop_interrupts_sequence():
    """Emergency stop during a preset sequence stops immediately and returns IDLE."""
    move_count = {"n": 0}
    stop_after_first = threading.Event()

    def move_impl(_sensors, _sensor_name, _target, ser, tolerance=2, timeout=30):
        move_count["n"] += 1
        if move_count["n"] == 1:
            stop_after_first.set()
            # Block until the test thread triggers emergency stop via the serial proxy
            while True:
                ser.write(b"x")
                time.sleep(0.01)
        return True

    wrapper_module, motor_control = _load_wrapper_module(
        move_impl=move_impl,
        retract_impl=lambda *_args, **_kwargs: True,
    )

    controller = wrapper_module.DeskControllerWrapper(log_file=None)
    controller.is_initialized = True
    controller.serial_port = Mock()
    controller.presets[1] = {1: 90.0, 2: 200.0, 3: 300.0}

    controller._mqtt_on_message(None, None, _Message(b"preset 1"))
    assert _wait_for(lambda: stop_after_first.is_set())

    controller._mqtt_on_message(None, None, _Message(b"emergency_stop"))
    assert _wait_for(lambda: controller.system_state == wrapper_module.SystemState.IDLE)
    motor_control.emergency_stop.assert_called()
    # Only the first motor (M2) should have started; M3 and M1 must not have run
    assert move_count["n"] == 1
