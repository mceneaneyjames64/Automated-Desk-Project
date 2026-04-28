"""
Tests for the sensor-read averaging inside _read_corrected().

Issue B fix: _read_corrected() now takes SENSOR_AVERAGE_SAMPLES readings and
averages them, so single-sample noise no longer drives bang-bang oscillation.

Issue D fix: the calibration offset (computed from a 30-sample average) is now
applied to an equally stable averaged value rather than a single noisy sample.
"""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch, call


def _load_motor_control():
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Stub hardware so the module loads without real I2C hardware
    fake_hardware = types.ModuleType("hardware")
    fake_hardware.get_sensor_value = lambda sensors, name: 0
    sys.modules["hardware"] = fake_hardware

    if "motor_control" in sys.modules:
        del sys.modules["motor_control"]

    return importlib.import_module("motor_control")


def test_read_corrected_calls_get_sensor_value_n_times():
    """_read_corrected must call get_sensor_value exactly SENSOR_AVERAGE_SAMPLES times."""
    mc = _load_motor_control()
    n = mc.config.SENSOR_AVERAGE_SAMPLES

    with patch.object(mc, "get_sensor_value", return_value=100) as mock_gsv:
        mc._read_corrected({}, mc.config.SENSOR_VL53_0)

    assert mock_gsv.call_count == n, (
        f"Expected {n} calls to get_sensor_value, got {mock_gsv.call_count}"
    )


def test_read_corrected_returns_average_plus_offset():
    """Returned value must equal mean(raw_samples) + offset."""
    mc = _load_motor_control()
    n = mc.config.SENSOR_AVERAGE_SAMPLES
    sensor = mc.config.SENSOR_VL53_0

    # Produce n readings that cycle through 98, 100, 102 … so mean is always 100.
    readings = [98 + (i % 3) * 2 for i in range(n)]
    expected_mean = sum(readings) / n
    offset = mc.config.OFFSET.get(sensor, 0)

    call_idx = [0]

    def sequential_readings(sensors, sensor_name):
        idx = call_idx[0]
        call_idx[0] += 1
        return readings[idx % len(readings)]

    with patch.object(mc, "get_sensor_value", side_effect=sequential_readings):
        result = mc._read_corrected({}, sensor)

    assert abs(result - (expected_mean + offset)) < 1e-9, (
        f"Expected {expected_mean + offset:.4f}, got {result:.4f}"
    )


def test_read_corrected_averages_reduce_noise_effect():
    """
    When the sensor oscillates around the true position by ±noise, the averaged
    reading must be closer to the true position than any individual noisy reading.
    """
    mc = _load_motor_control()
    n = mc.config.SENSOR_AVERAGE_SAMPLES
    sensor = mc.config.SENSOR_VL53_0

    true_pos = 150
    noise_amplitude = 4  # ±4 mm — worse than typical VL53L0X noise

    # Alternating +noise / -noise readings guarantee the mean is exact.
    noisy = [true_pos + (noise_amplitude if i % 2 == 0 else -noise_amplitude)
             for i in range(n)]

    call_idx = [0]

    def noisy_readings(sensors, sensor_name):
        idx = call_idx[0]
        call_idx[0] += 1
        return noisy[idx % len(noisy)]

    offset = mc.config.OFFSET.get(sensor, 0)

    with patch.object(mc, "get_sensor_value", side_effect=noisy_readings):
        result = mc._read_corrected({}, sensor)

    corrected_true = true_pos + offset
    assert abs(result - corrected_true) < noise_amplitude, (
        f"Averaged result {result:.2f} should be closer to true position "
        f"{corrected_true:.2f} than any single noisy reading (±{noise_amplitude} mm)"
    )


def test_read_corrected_no_offset_returns_raw_average():
    """When no calibration offset exists, the raw average is returned unchanged."""
    mc = _load_motor_control()
    n = mc.config.SENSOR_AVERAGE_SAMPLES
    sensor = mc.config.SENSOR_VL53_0

    # Temporarily remove offset for this sensor
    saved_offset = mc.config.OFFSET.get(sensor)
    mc.config.OFFSET.pop(sensor, None)

    try:
        with patch.object(mc, "get_sensor_value", return_value=75):
            result = mc._read_corrected({}, sensor)
    finally:
        if saved_offset is not None:
            mc.config.OFFSET[sensor] = saved_offset

    assert result == 75.0, f"Expected raw average 75.0, got {result}"


def test_sensor_average_samples_present_in_config():
    """config.SENSOR_AVERAGE_SAMPLES must exist and be a positive integer >= 2."""
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    config = importlib.import_module("config")
    assert hasattr(config, "SENSOR_AVERAGE_SAMPLES"), (
        "config.SENSOR_AVERAGE_SAMPLES not found"
    )
    n = config.SENSOR_AVERAGE_SAMPLES
    assert isinstance(n, int) and n >= 2, (
        f"SENSOR_AVERAGE_SAMPLES must be an integer >= 2, got {n!r}"
    )
