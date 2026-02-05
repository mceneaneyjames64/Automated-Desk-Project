# Hardware Control System Test Suite

Comprehensive test suite for the hardware control system including unit tests, integration tests, and hardware simulation.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Installation](#installation)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Writing New Tests](#writing-new-tests)
- [CI/CD Integration](#cicd-integration)

## 🎯 Overview

This test suite provides comprehensive testing for:
- Hardware initialization (I2C, sensors, motors)
- Sensor reading and calibration
- Motor control and positioning
- Error handling and recovery
- Safety interlocks
- Integration workflows

## 📁 Test Structure

```
.
├── test_hardware_system.py      # Unit tests for individual components
├── test_integration.py          # Integration tests with simulated hardware
├── pytest.ini                   # Pytest configuration
├── test_requirements.txt        # Test dependencies
├── run_tests.py                 # Test runner script
└── README_TESTS.md             # This file
```

### Test Files

#### `test_hardware_system.py`
Unit tests using mocks for:
- Hardware initialization (`TestHardwareInitialization`)
- Sensor reading (`TestSensorReading`)
- Calibration (`TestCalibration`)
- Motor control (`TestMotorControl`)
- Serial communication (`TestSerialCommunication`)
- Error handling (`TestErrorHandling`)

#### `test_integration.py`
Integration tests with simulated hardware:
- Complete calibration workflows
- Motor movement with feedback
- Multi-sensor coordination
- Error recovery procedures
- Safety interlocks
- Performance testing

## 🚀 Installation

### 1. Install Test Dependencies

```bash
pip install -r test_requirements.txt
```

### 2. Verify Installation

```bash
pytest --version
```

## 🧪 Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py --all

# Run quick smoke tests
python run_tests.py --quick
```

### Test Categories

```bash
# Unit tests only
python run_tests.py --unit

# Integration tests only
python run_tests.py --integration

# Safety-critical tests
python run_tests.py --safety

# Specific module tests
python run_tests.py --module motor
python run_tests.py --module calibration
```

### Advanced Options

```bash
# Run with coverage report
python run_tests.py --coverage

# Run tests in parallel (faster)
python run_tests.py --parallel

# Generate HTML report
python run_tests.py --html

# Run tests continuously (watch mode)
python run_tests.py --watch
```

### Direct Pytest Commands

```bash
# Run all tests with verbose output
pytest -v

# Run specific test file
pytest test_hardware_system.py -v

# Run specific test class
pytest test_hardware_system.py::TestMotorControl -v

# Run specific test function
pytest test_hardware_system.py::TestMotorControl::test_move_to_absolute_distance -v

# Run tests matching pattern
pytest -k "motor" -v

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Run with coverage
pytest --cov --cov-report=html
```

## 📊 Test Coverage

### Generate Coverage Report

```bash
python run_tests.py --coverage
```

This generates:
- Terminal coverage summary
- HTML coverage report in `htmlcov/index.html`

### View Coverage Report

```bash
# Open in browser (Linux/Mac)
xdg-open htmlcov/index.html    # Linux
open htmlcov/index.html         # Mac

# Or manually open htmlcov/index.html in your browser
```

### Coverage Goals

- **Overall Coverage**: > 80%
- **Critical Functions**: 100%
  - `emergency_stop()`
  - Safety interlocks
  - Calibration functions

## ✍️ Writing New Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestNewFeature:
    """Test suite for new feature"""
    
    def test_feature_basic_functionality(self):
        """Test basic feature operation"""
        # Arrange
        expected = "expected_value"
        
        # Act
        result = function_under_test()
        
        # Assert
        assert result == expected
    
    @patch('module.external_dependency')
    def test_feature_with_mock(self, mock_dependency):
        """Test feature with mocked dependency"""
        mock_dependency.return_value = "mocked_value"
        
        result = function_under_test()
        
        assert result == "expected_result"
        mock_dependency.assert_called_once()
```

### Test Markers

Add markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_test():
    pass

@pytest.mark.integration
def test_integration():
    pass

@pytest.mark.slow
def test_long_running():
    pass

@pytest.mark.safety
def test_safety_critical():
    pass
```

### Fixtures

Use fixtures for common setup:

```python
@pytest.fixture
def mock_sensors():
    """Fixture providing mock sensor objects"""
    return {
        'vl53l0x_0': Mock(),
        'adxl345': Mock()
    }

def test_with_fixture(mock_sensors):
    """Test using fixture"""
    result = read_sensor(mock_sensors, 'vl53l0x_0')
    assert result is not None
```

## 🔄 CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r test_requirements.txt
    
    - name: Run tests
      run: |
        python run_tests.py --all --coverage
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### GitLab CI Example

Create `.gitlab-ci.yml`:

```yaml
test:
  image: python:3.9
  
  before_script:
    - pip install -r test_requirements.txt
  
  script:
    - python run_tests.py --all --coverage
  
  coverage: '/TOTAL.*\s+(\d+%)$/'
  
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

## 🐛 Debugging Failed Tests

### Show More Information

```bash
# Show full traceback
pytest --tb=long

# Show captured stdout
pytest -s

# Show local variables
pytest -l

# Enable debugging on failure
pytest --pdb
```

### Common Issues

1. **Import Errors**
   - Ensure all dependencies installed: `pip install -r test_requirements.txt`
   - Check Python path: `echo $PYTHONPATH`

2. **Mock Issues**
   - Verify patch path matches actual import path
   - Check mock is applied before function call

3. **Timing Issues**
   - Add `@pytest.mark.slow` for long tests
   - Increase timeout: `@pytest.mark.timeout(30)`

## 📈 Performance Testing

Run performance benchmarks:

```bash
pytest test_integration.py::TestPerformance -v --benchmark-only
```

## 🔒 Safety Tests

Critical safety tests should always pass:

```bash
python run_tests.py --safety
```

Safety tests include:
- Emergency stop functionality
- Movement range limits
- Sensor fault detection
- Watchdog timeouts

## 📝 Test Reports

### HTML Report

```bash
python run_tests.py --html
```

Opens: `test_report.html`

### JSON Report

```bash
pytest --json-report --json-report-file=report.json
```

## 🤝 Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure all tests pass
3. Maintain >80% coverage
4. Add docstrings to test functions
5. Use appropriate markers

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Python Mock Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Docs](https://coverage.readthedocs.io/)

## 🆘 Getting Help

For issues with the test suite:

1. Check test output for error messages
2. Review relevant test documentation
3. Run with verbose mode: `pytest -v`
4. Check GitHub issues for similar problems

## 📄 License

This test suite is part of the hardware control system project.
