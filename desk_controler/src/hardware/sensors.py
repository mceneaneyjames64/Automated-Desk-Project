import time
import adafruit_vl53l0x
import adafruit_adxl34x

from utils.timeout import timeout, TimeoutError
from hardware.i2c_utils import require_address
import config
from utils import vector_to_degrees, z_axis_to_degrees


def retry_with_timeout(fn, name, retries=config.I2C_RETRIES,
                       retry_delay=config.RETRY_DELAY,
                       timeout_seconds=config.OPERATION_TIMEOUT):
    """Retry a function with timeout protection."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            with timeout(timeout_seconds, f"{name} timed out after {timeout_seconds}s"):
                return fn()
        except (TimeoutError, Exception) as e:
            last_exc = e
            print(f"{name} attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(retry_delay)
    raise RuntimeError(f"{name} failed after {retries} attempts: {last_exc}")


def read_with_timeout(fn, name, timeout_seconds=config.READ_TIMEOUT):
    """Read from sensor with timeout protection."""
    start = time.monotonic()
    while True:
        try:
            return fn()
        except Exception as e:
            if time.monotonic() - start > timeout_seconds:
                raise TimeoutError(f"{name} read timed out after {timeout_seconds}s: {e}")
            time.sleep(0.01)


def init_vl53l0x(tca, channel, name):
    """Initialize VL53L0X time-of-flight sensor."""
    print(f"Initializing {name}...")
    require_address(tca, channel, hex(config.VL53_ADDRESS), name)

    def _init():
        sensor = adafruit_vl53l0x.VL53L0X(tca[channel])
        sensor.measurement_timing_budget = config.VL53_TIMING_BUDGET
        sensor.signal_rate_limit = config.VL53_RATE_LIMIT
        sensor.sigma_limit = config.VL53_SIGMA_LIMIT
        read_with_timeout(lambda: sensor.range, f"{name} range validation")
        return sensor

    sensor = retry_with_timeout(_init, name)
    print(f"{name} initialized successfully")
    return sensor


def init_adxl345(tca):
    """Initialize ADXL345 accelerometer."""
    print("Initializing ADXL345 accelerometer...")
    require_address(tca, config.ADXL345_CHANNEL, hex(config.ADXL_ADDRESS), "ADXL345")

    def _init():
        sensor = adafruit_adxl34x.ADXL345(tca[config.ADXL345_CHANNEL])
        read_with_timeout(lambda: sensor.acceleration, "ADXL345 acceleration validation")
        return sensor

    sensor = retry_with_timeout(_init, "ADXL345")
    print("ADXL345 initialized successfully")
    return sensor


def get_sensor_value(sensors, sensor_name):
    """
    Get the current value from a named sensor.

    Parameters
    ----------
    sensors     : dict  — dictionary of initialised sensor objects.
    sensor_name : str   — one of the config.SENSOR_* constants.

    Returns
    -------
    int   : Distance in millimetres for VL53L0X sensors.
    float : Tilt angle in degrees for the ADXL345.

              Convention (Z-axis only):
                  0°   → sensor upside down   (Z ≈ −g)
                  90°  → sensor perpendicular  (Z ≈  0)
                  180° → sensor right-side up  (Z ≈ +g)
    """
    if sensor_name == config.SENSOR_VL53_0:
        return read_with_timeout(
            lambda: sensors[config.SENSOR_VL53_0].range,
            f"{config.SENSOR_VL53_0} range read",
        )

    elif sensor_name == config.SENSOR_VL53_1:
        return read_with_timeout(
            lambda: sensors[config.SENSOR_VL53_1].range,
            f"{config.SENSOR_VL53_1} range read",
        )

    elif sensor_name == config.SENSOR_ADXL:
        x, y, z = read_with_timeout(
            lambda: sensors[config.SENSOR_ADXL].acceleration,
            f"{config.SENSOR_ADXL} acceleration read",
        )
        return z_axis_to_degrees(z)

    else:
        raise RuntimeError(
            f"Sensor '{sensor_name}' is not recognised. "
            f"Valid names: {config.SENSOR_VL53_0!r}, "
            f"{config.SENSOR_VL53_1!r}, {config.SENSOR_ADXL!r}."
        )
