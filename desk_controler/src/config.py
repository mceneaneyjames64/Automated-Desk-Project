# I2C Configuration
I2C_RETRIES = 3
RETRY_DELAY = 0.2
OPERATION_TIMEOUT = 5
READ_TIMEOUT = 1.0

# VL53L0X Configuration

# Measurment timing budget (microseconds)
# Higher = more accurate
VL53_TIMING_BUDGET = 200000

# Signal rate limit (affects valid measurment threshold) (MCPS)
# Lower = more permissive (detects weak returns)
# Higher = stricted (better accuracy on clean targets)
# Range: 0.1 - 0.5
# For accuracy in solid targets, use 0.25 - 0.5
VL53_RATE_LIMIT = 0.25

# Enable sigma (noise) estimation limit (millimeters)
# Lower vlaue = only accept low-noise readings
VL53_SIGMA_LIMIT = 9

# I2C adress
VL53_ADDRESS = 0x29

# MUX channels
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
