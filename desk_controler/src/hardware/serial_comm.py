import serial
from utils.timeout import timeout, TimeoutError
import config


def init_serial(port=config.SERIAL_PORT, 
                baudrate=config.SERIAL_BAUDRATE, 
                init_timeout=3.0):
    """
    Initialize serial port with timeout protection
    
    Args:
        port (str): Serial port path
        baudrate (int): Baud rate
        init_timeout (float): Timeout for initialization
        
    Returns:
        serial.Serial object or None on failure
    """
    print(f"Initializing serial port {port}...")
    
    try:
        with timeout(init_timeout, f"Serial port {port} initialization timed out"):
            ser = serial.Serial(
                port,
                baudrate=baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=config.SERIAL_TIMEOUT
            )
            print(f"Serial port {ser.name} opened successfully")
            return ser
            
    except (serial.SerialException, TimeoutError) as e:
        print(f"Error opening serial port: {e}")
        return None
