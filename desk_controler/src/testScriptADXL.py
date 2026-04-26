###testScriptADXL

import time
from pathlib import Path
import sys

# Add src directory to path
src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))

import config
from hardware import init_i2c, init_mux, init_adxl345, get_sensor_value


def main():
    output_file = Path("adxl_i2c_data.csv")

    try:
        # Initialize hardware
        print("Initializing I2C and ADXL345...")
        i2c = init_i2c()
        tca = init_mux(i2c)
        sensors = {
            config.SENSOR_ADXL: init_adxl345(tca)
        }
        
        print(f"ADXL345 initialized successfully. Logging to {output_file}...\n")

        with open(output_file, "w") as f:
            f.write("timestamp,x,y,z,angle_deg\n")

            try:
                while True:
                    # Read raw acceleration data
                    x, y, z = sensors[config.SENSOR_ADXL].acceleration
                    timestamp = time.time()
                    
                    # Also get the computed angle
                    angle = get_sensor_value(sensors, config.SENSOR_ADXL)

                    f.write(f"{timestamp},{x:.3f},{y:.3f},{z:.3f},{angle:.1f}\n")
                    print(f"{timestamp:.3f}: X={x:.3f}g, Y={y:.3f}g, Z={z:.3f}g | Angle={angle:.1f}°")

                    time.sleep(0.1)  # 10 Hz sampling rate

            except KeyboardInterrupt:
                print("\n✓ Logging stopped. Data saved.")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
