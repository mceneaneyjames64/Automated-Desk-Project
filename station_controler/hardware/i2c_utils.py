import time
import board
import busio
import adafruit_tca9548a

from utils.timeout import timeout, TimeoutError
import config


def init_i2c(init_timeout=3.0):
    """Initialize I2C bus with timeout protection"""
    print("Initializing I2C bus...")
    
    with timeout(init_timeout, "I2C bus initialization timed out"):
        i2c = busio.I2C(board.SCL, board.SDA)
        start = time.monotonic()
        while not i2c.try_lock():
            if time.monotonic() - start > 2.0:
                raise TimeoutError("I2C bus lock timeout")
            time.sleep(0.01)
        i2c.unlock()
    
    print("I2C Bus opened successfully")
    return i2c


def init_mux(i2c, retries=config.I2C_RETRIES, retry_delay=config.RETRY_DELAY):
    """Initialize TCA9548A multiplexer"""
    print("Initializing TCA9548A multiplexer...")
    
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            with timeout(3, "TCA9548A initialization timed out"):
                tca = adafruit_tca9548a.TCA9548A(i2c)
                print("TCA9548A initialized successfully")
                return tca
        except Exception as e:
            last_exc = e
            print(f"TCA9548A attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(retry_delay)
    
    raise RuntimeError(f"TCA9548A init failed after {retries} attempts: {last_exc}")


def scan_i2c_channels(tca, timeout_per_channel=1.0):
    """Scan all TCA9548A channels for I2C devices"""
    print("\nScanning I2C channels...")
    for channel in range(8):
        try:
            with timeout(timeout_per_channel, f"Channel {channel} scan timeout"):
                if tca[channel].try_lock():
                    try:
                        addresses = tca[channel].scan()
                        devices = [hex(addr) for addr in addresses if addr != 0x70]
                        print(f"Channel {channel}: {devices if devices else 'No devices'}")
                    finally:
                        tca[channel].unlock()
        except TimeoutError as e:
            print(f"Channel {channel}: {e}")


def require_address(tca, channel, addr, name, retries=config.I2C_RETRIES, retry_delay=config.RETRY_DELAY):
    """Verify sensor address on specific channel"""
    def _check():
        if tca[channel].try_lock():
            try:
                addresses = tca[channel].scan()
                found = [hex(address) for address in addresses if address != 0x70]
            
                if addr not in found:
                    raise RuntimeError(
                        f"{name} not found on channel {channel} "
                        f"(expected {addr}, found {found})"
                    )
                else:
                    print(f"{name} found at {addr} on channel {channel}")
            finally:
                tca[channel].unlock()
        else:
            raise RuntimeError(f"Could not lock channel {channel}")
    
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            with timeout(2, f"{name} address check timed out"):
                _check()
                return
        except Exception as e:
            last_exc = e
            if attempt < retries:
                time.sleep(retry_delay)
    
    raise RuntimeError(f"{name} address check failed after {retries} attempts: {last_exc}")
