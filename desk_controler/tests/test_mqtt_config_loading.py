import importlib
import sys
import types
from pathlib import Path
from unittest.mock import Mock


def _install_mqtt_stubs():
    paho = types.ModuleType("paho")
    paho_mqtt = types.ModuleType("paho.mqtt")
    paho_mqtt_client = types.ModuleType("paho.mqtt.client")

    class _Client:
        pass

    class _CallbackAPIVersion:
        VERSION2 = 2

    paho_mqtt_client.Client = _Client
    paho_mqtt_client.CallbackAPIVersion = _CallbackAPIVersion
    paho_mqtt_client.MQTTv5 = object()

    sys.modules["paho"] = paho
    sys.modules["paho.mqtt"] = paho_mqtt
    sys.modules["paho.mqtt.client"] = paho_mqtt_client

    fake_motor_control = types.ModuleType("motor_control")
    fake_motor_control.move_to_distance = Mock(return_value=True)
    fake_motor_control.retract_fully = Mock(return_value=True)
    fake_motor_control.emergency_stop = Mock()
    fake_motor_control.stop = Mock()
    sys.modules["motor_control"] = fake_motor_control

    fake_calibration = types.ModuleType("calibration")
    fake_calibration.calibrate_vl53_sensors = Mock()
    sys.modules["calibration"] = fake_calibration

    return fake_motor_control, fake_calibration


def _import_mqtt_with_stubs():
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    fake_motor_control, fake_calibration = _install_mqtt_stubs()
    if "MQTT" in sys.modules:
        del sys.modules["MQTT"]

    mqtt_module = importlib.import_module("MQTT")
    return mqtt_module, fake_motor_control, fake_calibration


def test_mqtt_parameters_are_loaded_from_config_at_import_time(monkeypatch):
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    _install_mqtt_stubs()

    config = importlib.import_module("config")
    monkeypatch.setattr(config, "MQTT_BROKER", "runtime-broker")

    if "MQTT" in sys.modules:
        del sys.modules["MQTT"]

    mqtt_module = importlib.import_module("MQTT")

    assert mqtt_module.BROKER == config.MQTT_BROKER
    assert mqtt_module.PORT == config.MQTT_PORT
    assert mqtt_module.TOPIC_COMMAND == config.MQTT_TOPIC_COMMAND
    assert mqtt_module.TOPIC_STATUS == config.MQTT_TOPIC_STATUS
    assert mqtt_module.TOPIC_FEEDBACK == config.MQTT_TOPIC_FEEDBACK
    assert mqtt_module.USERNAME == config.MQTT_USERNAME
    assert mqtt_module.PASSWORD == config.MQTT_PASSWORD
    assert mqtt_module.PRESET_FILE == config.MQTT_PRESET_FILE
    assert mqtt_module.HEARTBEAT_INTERVAL == config.MQTT_HEARTBEAT_INTERVAL


def test_stop_payload_calls_normal_stop_handler():
    mqtt_module, fake_motor_control, _ = _import_mqtt_with_stubs()

    mqtt_module.motor_serial_port = object()
    client = Mock()
    message = types.SimpleNamespace(payload=b"stop")

    mqtt_module.on_message(client, None, message)

    fake_motor_control.stop.assert_called_once_with(mqtt_module.motor_serial_port)
    client.publish.assert_called_with(mqtt_module.TOPIC_STATUS, "STOP")


def test_emergency_stop_payload_calls_emergency_stop_handler():
    mqtt_module, fake_motor_control, _ = _import_mqtt_with_stubs()

    mqtt_module.motor_serial_port = object()
    client = Mock()
    message = types.SimpleNamespace(payload=b"emergency_stop")

    mqtt_module.on_message(client, None, message)

    fake_motor_control.emergency_stop.assert_called_once_with(mqtt_module.motor_serial_port)
    client.publish.assert_called_with(mqtt_module.TOPIC_STATUS, "EMERGENCY STOP")


def test_calibrate_payload_runs_calibration_script():
    mqtt_module, _, fake_calibration = _import_mqtt_with_stubs()

    mqtt_module.calibration_sensors = {"test_sensor": object()}
    client = Mock()
    message = types.SimpleNamespace(payload=b"calibrate")

    mqtt_module.on_message(client, None, message)

    fake_calibration.calibrate_vl53_sensors.assert_called_once_with(mqtt_module.calibration_sensors)
    client.publish.assert_called_with(mqtt_module.TOPIC_STATUS, "Calibration complete")


def test_m2_down_payload_calls_retract_fully_with_vl53_sensor():
    mqtt_module, fake_motor_control, _ = _import_mqtt_with_stubs()

    sensors = {"vl53l0x_0": object()}
    mqtt_module.motor_sensors = sensors
    mqtt_module.motor_serial_port = object()
    client = Mock()
    message = types.SimpleNamespace(payload=b"m2 -> down")

    mqtt_module.on_message(client, None, message)

    fake_motor_control.retract_fully.assert_called_once_with(
        sensors, mqtt_module.config.SENSOR_VL53_0, mqtt_module.motor_serial_port
    )
    client.publish.assert_called_with(mqtt_module.TOPIC_STATUS, "M2 retracting...")


def test_m2_up_payload_calls_move_to_distance_with_max_position():
    mqtt_module, fake_motor_control, _ = _import_mqtt_with_stubs()

    sensors = {"vl53l0x_0": object()}
    mqtt_module.motor_sensors = sensors
    mqtt_module.motor_serial_port = object()
    client = Mock()
    message = types.SimpleNamespace(payload=b"m2 -> up")

    mqtt_module.on_message(client, None, message)

    fake_motor_control.move_to_distance.assert_called_once_with(
        sensors,
        mqtt_module.config.SENSOR_VL53_0,
        mqtt_module.config.MAX_POSITION,
        mqtt_module.motor_serial_port,
    )
    client.publish.assert_called_with(mqtt_module.TOPIC_STATUS, "M2 extending...")


def test_m2_numeric_payload_calls_move_to_distance_with_requested_position():
    mqtt_module, fake_motor_control, _ = _import_mqtt_with_stubs()

    sensors = {"vl53l0x_0": object()}
    mqtt_module.motor_sensors = sensors
    mqtt_module.motor_serial_port = object()
    client = Mock()
    message = types.SimpleNamespace(payload=b"m2 -> 123.4")

    mqtt_module.on_message(client, None, message)

    fake_motor_control.move_to_distance.assert_called_once_with(
        sensors,
        mqtt_module.config.SENSOR_VL53_0,
        123.4,
        mqtt_module.motor_serial_port,
    )
    client.publish.assert_called_with(mqtt_module.TOPIC_STATUS, "M2 moving to 123.4mm...")
