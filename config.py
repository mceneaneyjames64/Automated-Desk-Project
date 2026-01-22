# I2C Configuration
I2C_RETRIES = 3
RETRY_DELAY = 0.2
OPERATION_TIMEOUT = 5
READ_TIMEOUT = 1.0

# VL53L0X Configuration
VL53_TIMING_BUDGET = 100000
VL53_ADDRESS = 0x29
VL53_CHANNEL_1 = 0
VL53_CHANNEL_2 = 1

# ADXL345 Configuration
ADXL_ADDRESS = 0x53
ADXL_CHANNEL = 2

# Serial Configuration
SERIAL_PORT = '/dev/serial0'
SERIAL_BAUDRATE = 2400
SERIAL_TIMEOUT = 1

# Motor Control Commands
OFF    = b'\x5a\x00\x5a'
M1_OUT = b'\x5a\x01\x5b'
M1_IN  = b'\x5a\x02\x5c'
M2_OUT = b'\x5a\x04\x5e'
M2_IN  = b'\x5a\x08\x62'
M3_OUT = b'\x5a\x10\x6a'
M3_IN  = b'\x5a\x20\x7a'

# Position Limits
MIN_POSITION = 20
MAX_POSITION = 390
