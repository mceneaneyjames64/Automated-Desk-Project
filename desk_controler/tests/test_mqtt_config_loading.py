from pathlib import Path


def test_mqtt_parameters_are_loaded_from_config_with_local_runtime_assignments():
    mqtt_path = Path(__file__).resolve().parents[1] / "src" / "MQTT.py"
    source = mqtt_path.read_text()

    assert "BROKER = config.MQTT_BROKER" in source
    assert "PORT = config.MQTT_PORT" in source
    assert "TOPIC_COMMAND = config.MQTT_TOPIC_COMMAND" in source
    assert "TOPIC_STATUS = config.MQTT_TOPIC_STATUS" in source
    assert "TOPIC_FEEDBACK = config.MQTT_TOPIC_FEEDBACK" in source
    assert "USERNAME = config.MQTT_USERNAME" in source
    assert "PASSWORD = config.MQTT_PASSWORD" in source
    assert "PRESET_FILE = config.MQTT_PRESET_FILE" in source
    assert "HEARTBEAT_INTERVAL = config.MQTT_HEARTBEAT_INTERVAL" in source
