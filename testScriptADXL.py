### Test Script for ADXL sensor 

import time
from pathlib import Path
import sys

# Add src directory
src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))

from sensors.adxl import read_adxl


def main():
    output_file = Path("adxl_i2c_data.csv")

    with open(output_file, "w") as f:
        f.write("timestamp,x,y,z\n")

        print("Starting ADXL I2C logging... (Ctrl+C to stop)")

        try:
            while True:
                x, y, z = read_adxl()
                timestamp = time.time()

                f.write(f"{timestamp},{x},{y},{z}\n")
                print(f"{timestamp:.3f}: X={x:.3f}, Y={y:.3f}, Z={z:.3f}")

                time.sleep(0.1)  # 10 Hz

        except KeyboardInterrupt:
            print("\nLogging stopped. Data saved to file.")


if __name__ == "__main__":
    main()