# Desk Controller System

> **Automated height-adjustable desk controller with precision positioning, multi-sensor feedback, and remote MQTT control**

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/) ![License](https://img.shields.io/badge/license-MIT-green.svg) 

---

## Table of Contents

-   [Overview](#-overview)
-   [Features](#-features)
-   [Hardware Requirements](#-hardware-requirements)
-   [System Architecture](#-system-architecture)
-   [Installation](#-installation)
-   [License](#-license)

----------

##  Overview

The Desk Controller System is a comprehensive hardware control system:

-   **Precision positioning** using dual VL53L0X laser distance sensors
-   **Angle positioning** via ADXL345 accelerometer
-   **Closed-loop motor control** with real-time feedback
-   **Calibration system** for accurate baseline positioning
-   **Remote control** via MQTT protocol
-   **Safety features** including emergency stops and range limits
-   **Comprehensive testing** with unit and integration test suites

## Features

### Core Features

-    **Dual Distance Sensing** - VL53L0X sensors for height
-    **Angle Sensing** - ADXL345 accelerometer for tilt
-    **Automated Calibration** - Self-calibrating baseline position system
-    **Closed-Loop Control** - Real-time position feedback and correction
-    **Serial Motor Control** - Direct motor controller communication
-    **MQTT Support** - Remote control and status monitoring
-    **Safety Interlocks** - Emergency stop, range limits, timeout protection

### Advanced Features

-    **Position Memory** - Save and recall favorite positions
-    **Automatic Recovery** - Handles sensor/communication errors gracefully
-   **Comprehensive Testing** - 100+ unit and integration tests
-    **Fast Response** - <100ms sensor reading time
-    **Robust Error Handling** - Retry mechanisms and timeout protection

----------

##  Hardware Requirements

### Required Components

|Component | Quantity | Specification | Purpose|
|:---|:---|:---|:---|
| Raspberry Pi | 1 | Pi 3/4/Zero 2W | Main controller |
| VL53L0X | 2 | Time-of-Flight sensor | Distance measurement |
| ADXL345 | 1 | 3-axis accelerometer | Motion/tilt detection|
| TCA9548A | 1 | I2C multiplexer | Multi-sensor addressing |
| Motor Controller | 1 | Serial/UART interface | Actuator control |
| Linear Actuator | 1-3 | 12V/24V DC | Height adjustment |
| Power Supply | 1 | 12V/24V, 5A+ | Motor power |

### Wiring Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi                         │
│                                                         │
│  GPIO2/3 (I2C)              GPIO14/15 (UART)            │
└────┬────────────────────────────────┬───────────────────┘
     │                                │
     │ I2C Bus                        │ Serial
     │ (SDA/SCL)                      │
     ▼                                ▼
┌────────────┐                  ┌──────────────┐
│  TCA9548A  │                  │    Motor     │
│    MUX     │                  │  Controller  │
└─┬─┬─┬──────┘                  └──────┬───────┘
  │ │ │                                │
  │ │ └─ Ch2: ADXL345                  │
  │ └─── Ch1: VL53L0X #2               ▼
  └───── Ch0: VL53L0X #1          ┌─────────┐
                                  │ Actuator│
                                  └─────────┘

```

### Pin Connections

**Raspberry Pi GPIO:**

```
GPIO 2  → I2C SDA  (to TCA9548A)
GPIO 3  → I2C SCL  (to TCA9548A)
GPIO 14 → UART TX  (to Motor Controller)
GPIO 15 → UART RX  (to Motor Controller)
3.3V    → VCC      (sensors)
GND     → GND      (all components)

```

**TCA9548A Channels:**

```
Channel 0 → VL53L0X #1 (0x29)
Channel 1 → VL53L0X #2 (0x29)
Channel 2 → ADXL345    (0x53)

```

----------

## System Architecture

### Software Architecture

```
┌────────────────────────────────────────────────────────┐
│                     Application Layer                  │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  main.py │  │ MQTT Client  │  │  Test Suite     │   │
│  └────┬─────┘  └──────┬───────┘  └─────────────────┘   │
└───────┼───────────────┼──────────────────────────────┬─┘
        │               │                              │
┌───────▼───────────────▼──────────────────────────────▼─┐
│                   Control Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │motor_control │  │ calibration  │  │    config    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────────────────────────────────────────┘
        │                │                │
┌───────▼────────────────▼────────────────▼───────────────┐
│                   Hardware Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ sensors  │  │ i2c_utils│  │serial_comm│              │
│  └──────────┘  └──────────┘  └──────────┘               │
└─────────────────────────────────────────────────────────┘
        │                │                │
┌───────▼────────────────▼────────────────▼───────────────┐
│                   Physical Layer                        │
│         VL53L0X    ADXL345    Motor Controller          │
└─────────────────────────────────────────────────────────┘

```

### Directory Structure

```
Automated-Desk-Project/           # Repository root
├── README.md                     # This file
├── heartbeat-handler.py          # Standalone heartbeat monitor
│
└── desk_controler/               # Main controller application
    ├── README.md                 # Detailed technical architecture
    ├── src/                      # Source code
    │   ├── main.py               # Main application entry point
    │   ├── config.py             # Configuration constants & commands
    │   ├── calibration.py        # VL53L0X calibration routines
    │   ├── motor_control.py      # Motor control logic
    │   ├── desk_controller_wrapper.py  # High-level control wrapper
    │   ├── desk_controller_service.py  # Background service
    │   ├── MQTT.py               # MQTT client integration
    │   ├── requirements.txt      # Python dependencies
    │   ├── hardware/             # Hardware interface modules
    │   │   ├── __init__.py
    │   │   ├── i2c_utils.py      # I2C and multiplexer utilities
    │   │   ├── sensors.py        # Sensor initialization/reading
    │   │   └── serial_comm.py    # Serial communication
    │   └── utils/                # Utility functions
    │       ├── __init__.py
    │       ├── timeout.py        # Timeout handling
    │       └── misc.py           # Angle conversion helpers
    │
    ├── tests/                    # Test suite
    │   ├── test_hardware_system.py           # Unit tests
    │   ├── test_integration.py               # Integration tests
    │   ├── test_desk_controller_wrapper_mqtt_async.py
    │   ├── test_mqtt_config_loading.py
    │   ├── test_config_motor_sensor_mapping.py
    │   ├── test_motor_control_retract_minimum.py
    │   ├── test_drift.py
    │   ├── test_requirements.txt             # Test dependencies
    │   ├── run_tests.py                      # Test runner
    │   ├── pytest.ini                        # Pytest configuration
    │   └── README.md                         # Test documentation
    │
    └── docs/                     # Additional documentation
        ├── quickstart_guide.md   # Step-by-step setup guide
        ├── Calibration.md        # Calibration procedures
        ├── Examples.md           # Usage examples
        ├── Key_concepts.md       # Core concepts explained
        └── Troubleshooting Guide.md  # Troubleshooting reference

```

----------

##  Installation

### Prerequisites

-   Raspberry Pi OS (Buster or newer)
-   Python 3.7 or higher
-   I2C enabled on Raspberry Pi
-   Serial port enabled

### Enable I2C and Serial

```bash
# Open raspi-config
sudo raspi-config

# Navigate to:
# 3. Interface Options → I2C → Enable
# 3. Interface Options → Serial → Disable login shell, Enable serial port

# Reboot
sudo reboot

```

### Install System Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install I2C tools
sudo apt-get install -y i2c-tools python3-pip python3-venv

# Verify I2C devices
i2cdetect -y 1

```

### Install Project

```bash
# Clone repository
git clone https://github.com/mceneaneyjames64/Automated-Desk-Project.git
cd Automated-Desk-Project/desk_controler/src

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
cd src
pip install -r requirements.txt

# Install test dependencies (optional)
cd ../tests
pip install -r test_requirements.txt

```

### Verify Installation

```bash
# Check I2C devices (should show TCA9548A at 0x70)
i2cdetect -y 1

# Run quick hardware test
cd ../src
python3 -c "from hardware import init_i2c; init_i2c()"

```
## License

This project is licensed under the MIT License - see the LICENSE file for details.


## Support

**Issues:** https://github.com/mceneaneyjames64/Automated-Desk-Project/issues

### Documentation

| Document | Description |
|----------|-------------|
| [desk_controler/README.md](desk_controler/README.md) | Detailed technical architecture, hardware components, code flow, and API reference |
| [docs/quickstart_guide.md](desk_controler/docs/quickstart_guide.md) | Step-by-step setup guide — get running in 15 minutes |
| [docs/Calibration.md](desk_controler/docs/Calibration.md) | Full sensor calibration procedures |
| [docs/Examples.md](desk_controler/docs/Examples.md) | Usage examples and common patterns |
| [docs/Key_concepts.md](desk_controler/docs/Key_concepts.md) | I2C, multiplexers, angle sensing, closed-loop control explained |
| [docs/Troubleshooting Guide.md](desk_controler/docs/Troubleshooting%20Guide.md) | Solutions to common hardware and software issues |
| [tests/README.md](desk_controler/tests/README.md) | Test suite documentation |


