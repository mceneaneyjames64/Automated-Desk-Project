import sys
from hardware import (
    init_i2c, 
    init_mux, 
    scan_i2c_channels,
    init_vl53l0x,
    init_adxl345,
    init_serial,
    get_current_position
)
import config


def init_all_hardware():
    """Initialize all hardware components"""
    sensors = {}
    
    # Initialize I2C and multiplexer
    i2c = init_i2c()
    tca = init_mux(i2c)
    sensors["mux"] = tca
    
    # Initialize VL53L0X sensors
    sensors["vl53l0x_0"] = init_vl53l0x(tca, config.VL53_CHANNEL_1, "VL53L0X #1")
    sensors["vl53l0x_1"] = init_vl53l0x(tca, config.VL53_CHANNEL_2, "VL53L0X #2")
    
    # Initialize ADXL345
    sensors["adxl345"] = init_adxl345(tca)
    
    print("\n All hardware successfully initialized\n")
    return sensors


def main():
    """Main program"""
    try:
        # Initialize hardware
        sensors = init_all_hardware()
        
        # Scan I2C channels
        scan_i2c_channels(sensors["mux"])
        
        # Test sensor readings
        print("\nTesting sensor readings...")
        print(f"VL53L0X #1 range: {sensors['vl53l0x_0'].range} mm")
        print(f"VL53L0X #2 range: {sensors['vl53l0x_1'].range} mm")
        print(f"ADXL345 acceleration: {sensors['adxl345'].acceleration}")
        
        # Initialize serial if needed
        # ser = init_serial()
        
        print("\n System ready")
        return 0
        
    except Exception as e:
        print(f"\n Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
