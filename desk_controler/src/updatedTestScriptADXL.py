import time
from pathlib import Path
import sys
from statistics import mean, stdev
from datetime import datetime

# Add src directory to path
src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))

import config
from hardware import init_i2c, init_mux, init_adxl345, get_sensor_value


def main():
    # Output files
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_file = Path(f"adxl_data_{timestamp_str}.csv")
    report_file = Path(f"adxl_report_{timestamp_str}.csv")

    try:
        # Initialize hardware
        print("Initializing I2C and ADXL345...")
        i2c = init_i2c()
        tca = init_mux(i2c)
        sensors = {
            config.SENSOR_ADXL: init_adxl345(tca)
        }
        
        print(f"✓ ADXL345 initialized successfully")
        print(f"✓ Data file:   {data_file}")
        print(f"✓ Report file: {report_file}")
        print(f"✓ Sampling at 1 Hz (1 second intervals)")
        print(f"✓ Press Ctrl+C to stop\n")

        samples = {
            'timestamp': [],
            'x': [],
            'y': [],
            'z': [],
            'angle': []
        }

        with open(data_file, "w") as f:
            f.write("timestamp,x,y,z,angle_deg\n")
            f.flush()

            try:
                sample_count = 0
                start_time = time.time()
                
                print("Starting data collection...")
                print("-" * 80)
                
                while True:
                    # Read raw acceleration data
                    x, y, z = sensors[config.SENSOR_ADXL].acceleration
                    timestamp = time.time()
                    
                    # Get the computed angle
                    angle = get_sensor_value(sensors, config.SENSOR_ADXL)

                    # Store for statistics
                    samples['timestamp'].append(timestamp)
                    samples['x'].append(x)
                    samples['y'].append(y)
                    samples['z'].append(z)
                    samples['angle'].append(angle)

                    # Write to data file
                    f.write(f"{timestamp:.3f},{x:.3f},{y:.3f},{z:.3f},{angle:.1f}\n")
                    f.flush()
                    
                    # Print to console
                    elapsed = timestamp - start_time
                    print(f"[{sample_count:4d}] {elapsed:7.2f}s | "
                          f"X={x:+6.3f}g Y={y:+6.3f}g Z={z:+6.3f}g | "
                          f"Angle={angle:6.1f}°")

                    sample_count += 1
                    time.sleep(1.0)  # 1 Hz sampling rate (1 second intervals)

            except KeyboardInterrupt:
                print("-" * 80)
                print(f"\n✓ Logging stopped after {sample_count} samples")
                print(f"✓ Total duration: {samples['timestamp'][-1] - samples['timestamp'][0]:.2f}s\n")

                # Calculate statistics
                stats = calculate_statistics(samples, sample_count)
                
                # Print summary to console
                print_console_summary(stats)
                
                # Generate CSV report
                generate_csv_report(report_file, stats, sample_count)
                
                print(f"\n✓ Data saved to:   {data_file}")
                print(f"✓ Report saved to: {report_file}\n")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


def calculate_statistics(samples, sample_count):
    """Calculate statistics from collected samples."""
    if sample_count < 2:
        return None
    
    return {
        'duration': samples['timestamp'][-1] - samples['timestamp'][0],
        'samples': sample_count,
        'x': {
            'mean': mean(samples['x']),
            'stdev': stdev(samples['x']),
            'min': min(samples['x']),
            'max': max(samples['x']),
            'range': max(samples['x']) - min(samples['x']),
        },
        'y': {
            'mean': mean(samples['y']),
            'stdev': stdev(samples['y']),
            'min': min(samples['y']),
            'max': max(samples['y']),
            'range': max(samples['y']) - min(samples['y']),
        },
        'z': {
            'mean': mean(samples['z']),
            'stdev': stdev(samples['z']),
            'min': min(samples['z']),
            'max': max(samples['z']),
            'range': max(samples['z']) - min(samples['z']),
        },
        'angle': {
            'mean': mean(samples['angle']),
            'stdev': stdev(samples['angle']),
            'min': min(samples['angle']),
            'max': max(samples['angle']),
            'range': max(samples['angle']) - min(samples['angle']),
        }
    }


def print_console_summary(stats):
    """Print statistics summary to console."""
    if not stats:
        return
    
    print("=" * 80)
    print("📊 TEST STATISTICS")
    print("=" * 80)
    
    print(f"\nTest Duration: {stats['duration']:.2f}s ({stats['samples']} samples @ 1 Hz)\n")
    
    print("X Acceleration (m/s² or 'g'):")
    print(f"  Mean:       {stats['x']['mean']:+.4f}g")
    print(f"  Std Dev:    {stats['x']['stdev']:.4f}g")
    print(f"  Min:        {stats['x']['min']:+.4f}g")
    print(f"  Max:        {stats['x']['max']:+.4f}g")
    print(f"  Range:      {stats['x']['range']:.4f}g")
    
    print("\nY Acceleration (m/s² or 'g'):")
    print(f"  Mean:       {stats['y']['mean']:+.4f}g")
    print(f"  Std Dev:    {stats['y']['stdev']:.4f}g")
    print(f"  Min:        {stats['y']['min']:+.4f}g")
    print(f"  Max:        {stats['y']['max']:+.4f}g")
    print(f"  Range:      {stats['y']['range']:.4f}g")
    
    print("\nZ Acceleration (m/s² or 'g'):")
    print(f"  Mean:       {stats['z']['mean']:+.4f}g")
    print(f"  Std Dev:    {stats['z']['stdev']:.4f}g")
    print(f"  Min:        {stats['z']['min']:+.4f}g")
    print(f"  Max:        {stats['z']['max']:+.4f}g")
    print(f"  Range:      {stats['z']['range']:.4f}g")
    print(f"  Expected:   +9.81g (gravity)")
    print(f"  Z Drift:    {abs(stats['z']['mean'] - 9.81):.4f}g from expected")
    
    print("\nTilt Angle (degrees):")
    print(f"  Mean:       {stats['angle']['mean']:6.1f}°")
    print(f"  Std Dev:    {stats['angle']['stdev']:6.2f}°")
    print(f"  Min:        {stats['angle']['min']:6.1f}°")
    print(f"  Max:        {stats['angle']['max']:6.1f}°")
    print(f"  Range:      {stats['angle']['range']:6.2f}°")
    
    print("\n" + "=" * 80)
    
    # Health assessment
    print("\n🔍 HEALTH ASSESSMENT:")
    
    if stats['angle']['stdev'] < 0.5:
        print("  ✓ Angle stability:     EXCELLENT (< 0.5° std dev)")
    elif stats['angle']['stdev'] < 1.0:
        print("  ✓ Angle stability:     GOOD (< 1.0° std dev)")
    elif stats['angle']['stdev'] < 2.0:
        print("  ⚠ Angle stability:     ACCEPTABLE (< 2.0° std dev)")
    else:
        print(f"  ✗ Angle stability:     POOR ({stats['angle']['stdev']:.2f}° std dev)")
    
    z_drift = abs(stats['z']['mean'] - 9.81)
    if z_drift < 0.1:
        print("  ✓ Z-axis calibration:  EXCELLENT (< 0.1g drift)")
    elif z_drift < 0.2:
        print("  ✓ Z-axis calibration:  GOOD (< 0.2g drift)")
    else:
        print(f"  ⚠ Z-axis calibration:  CHECK MOUNT ({z_drift:.3f}g drift from 9.81g)")
    
    if stats['x']['stdev'] < 0.05 and stats['y']['stdev'] < 0.05:
        print("  ✓ XY noise:            LOW (< 0.05g std dev)")
    elif stats['x']['stdev'] < 0.1 and stats['y']['stdev'] < 0.1:
        print("  ✓ XY noise:            MODERATE (< 0.1g std dev)")
    else:
        print(f"  ⚠ XY noise:            HIGH (X: {stats['x']['stdev']:.3f}g, Y: {stats['y']['stdev']:.3f}g)")
    
    print()


def generate_csv_report(report_file, stats, sample_count):
    """Generate a CSV report with test results."""
    if not stats:
        return
    
    with open(report_file, "w") as f:
        f.write("ADXL345 Sensor Test Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("TEST SUMMARY\n")
        f.write("Metric,Value,Unit\n")
        f.write(f"Test Duration,{stats['duration']:.2f},seconds\n")
        f.write(f"Sample Count,{sample_count},samples\n")
        f.write(f"Sampling Rate,1,Hz\n\n")
        
        f.write("X ACCELERATION STATISTICS\n")
        f.write("Metric,Value,Unit\n")
        f.write(f"Mean,{stats['x']['mean']:+.4f},g\n")
        f.write(f"Standard Deviation,{stats['x']['stdev']:.4f},g\n")
        f.write(f"Minimum,{stats['x']['min']:+.4f},g\n")
        f.write(f"Maximum,{stats['x']['max']:+.4f},g\n")
        f.write(f"Range,{stats['x']['range']:.4f},g\n\n")
        
        f.write("Y ACCELERATION STATISTICS\n")
        f.write("Metric,Value,Unit\n")
        f.write(f"Mean,{stats['y']['mean']:+.4f},g\n")
        f.write(f"Standard Deviation,{stats['y']['stdev']:.4f},g\n")
        f.write(f"Minimum,{stats['y']['min']:+.4f},g\n")
        f.write(f"Maximum,{stats['y']['max']:+.4f},g\n")
        f.write(f"Range,{stats['y']['range']:.4f},g\n\n")
        
        f.write("Z ACCELERATION STATISTICS\n")
        f.write("Metric,Value,Unit\n")
        f.write(f"Mean,{stats['z']['mean']:+.4f},g\n")
        f.write(f"Standard Deviation,{stats['z']['stdev']:.4f},g\n")
        f.write(f"Minimum,{stats['z']['min']:+.4f},g\n")
        f.write(f"Maximum,{stats['z']['max']:+.4f},g\n")
        f.write(f"Range,{stats['z']['range']:.4f},g\n")
        f.write(f"Expected Value,9.8100,g\n")
        f.write(f"Drift from Expected,{abs(stats['z']['mean'] - 9.81):.4f},g\n\n")
        
        f.write("TILT ANGLE STATISTICS\n")
        f.write("Metric,Value,Unit\n")
        f.write(f"Mean,{stats['angle']['mean']:.1f},degrees\n")
        f.write(f"Standard Deviation,{stats['angle']['stdev']:.2f},degrees\n")
        f.write(f"Minimum,{stats['angle']['min']:.1f},degrees\n")
        f.write(f"Maximum,{stats['angle']['max']:.1f},degrees\n")
        f.write(f"Range,{stats['angle']['range']:.2f},degrees\n\n")
        
        f.write("SENSOR HEALTH ASSESSMENT\n")
        f.write("Category,Status,Details\n")
        
        if stats['angle']['stdev'] < 0.5:
            angle_status = "EXCELLENT"
        elif stats['angle']['stdev'] < 1.0:
            angle_status = "GOOD"
        elif stats['angle']['stdev'] < 2.0:
            angle_status = "ACCEPTABLE"
        else:
            angle_status = "POOR"
        f.write(f"Angle Stability,{angle_status},{stats['angle']['stdev']:.2f}° std dev\n")
        
        z_drift = abs(stats['z']['mean'] - 9.81)
        if z_drift < 0.1:
            z_status = "EXCELLENT"
        elif z_drift < 0.2:
            z_status = "GOOD"
        else:
            z_status = "CHECK MOUNT"
        f.write(f"Z-Axis Calibration,{z_status},{z_drift:.4f}g drift\n")
        
        if stats['x']['stdev'] < 0.05 and stats['y']['stdev'] < 0.05:
            xy_status = "LOW"
        elif stats['x']['stdev'] < 0.1 and stats['y']['stdev'] < 0.1:
            xy_status = "MODERATE"
        else:
            xy_status = "HIGH"
        f.write(f"XY Noise,{xy_status},X:{stats['x']['stdev']:.3f}g Y:{stats['y']['stdev']:.3f}g\n")


if __name__ == "__main__":
    sys.exit(main())
