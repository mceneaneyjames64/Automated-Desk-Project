### Calibration Curve for ADXL

import time


def calibrate_adxl(read_func, samples=50, delay=0.01):
    """
    Performs 2-point calibration (+1g and -1g) for X, Y, Z axes.

    read_func: function that returns (x, y, z)
    samples: number of samples to average per position
    delay: delay between samples

    Returns:
        dict with scale and offset for each axis
    """

    def collect_axis(prompt):
        input(f"\n{prompt} and press ENTER...")

        vals = []
        for _ in range(samples):
            vals.append(read_func())
            time.sleep(delay)

        avg_x = sum(v[0] for v in vals) / samples
        avg_y = sum(v[1] for v in vals) / samples
        avg_z = sum(v[2] for v in vals) / samples

        print(f"Captured avg: X={avg_x:.3f}, Y={avg_y:.3f}, Z={avg_z:.3f}")
        return avg_x, avg_y, avg_z

    # Collect +1g and -1g for each axis
    print("=== ADXL 2-Point Calibration ===")

    x_pos = collect_axis("Place +X axis UP (+1g on X)")
    x_neg = collect_axis("Place +X axis DOWN (-1g on X)")

    y_pos = collect_axis("Place +Y axis UP (+1g on Y)")
    y_neg = collect_axis("Place +Y axis DOWN (-1g on Y)")

    z_pos = collect_axis("Place +Z axis UP (+1g on Z)")
    z_neg = collect_axis("Place +Z axis DOWN (-1g on Z)")

    def compute(pos, neg):
        scale = 2.0 / (pos - neg)
        offset = 1.0 - (scale * pos)
        return scale, offset

    cal = {
        "x": compute(x_pos[0], x_neg[0]),
        "y": compute(y_pos[1], y_neg[1]),
        "z": compute(z_pos[2], z_neg[2]),
    }

    print("\n=== Calibration Results ===")
    for axis in ["x", "y", "z"]:
        s, o = cal[axis]
        print(f"{axis.upper()}: scale={s:.6f}, offset={o:.6f}")

    return cal

"""
### Apply calibration (plug into your pipeline) 

 def apply_calibration(x, y, z, cal):
    x_c = x * cal["x"][0] + cal["x"][1]
    y_c = y * cal["y"][0] + cal["y"][1]
    z_c = z * cal["z"][0] + cal["z"][1]
    return x_c, y_c, z_c

"""

"""
### Example usage with your I2C ADXL

from sensors.adxl import read_adxl

# Step 1: Run calibration once
cal = calibrate_adxl(read_adxl)

# Step 2: Use it in your loop
while True:
    x, y, z = read_adxl()
    x_c, y_c, z_c = apply_calibration(x, y, z, cal)

    print(f"Calibrated: X={x_c:.3f}, Y={y_c:.3f}, Z={z_c:.3f}")
"""