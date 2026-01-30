#!/usr/bin/env python3
"""
Test Runner for Hardware Control System
Provides convenient commands for running different test suites
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode != 0:
        print(f"\n❌ {description} FAILED")
        return False
    else:
        print(f"\n✅ {description} PASSED")
        return True


def run_all_tests():
    """Run complete test suite"""
    return run_command(
        "pytest test_hardware_system.py test_integration.py -v --cov",
        "Complete Test Suite"
    )


def run_unit_tests():
    """Run only unit tests"""
    return run_command(
        "pytest test_hardware_system.py -v -m 'not integration'",
        "Unit Tests"
    )


def run_integration_tests():
    """Run only integration tests"""
    return run_command(
        "pytest test_integration.py -v",
        "Integration Tests"
    )


def run_specific_module(module):
    """Run tests for a specific module"""
    return run_command(
        f"pytest -k {module} -v",
        f"Tests for {module}"
    )


def run_with_coverage():
    """Run tests with detailed coverage report"""
    success = run_command(
        "pytest test_hardware_system.py test_integration.py --cov --cov-report=html --cov-report=term-missing",
        "Tests with Coverage"
    )
    
    if success:
        print("\n📊 Coverage report generated in: htmlcov/index.html")
    
    return success


def run_safety_tests():
    """Run safety-critical tests"""
    return run_command(
        "pytest -m safety -v",
        "Safety-Critical Tests"
    )


def run_quick_tests():
    """Run quick smoke tests"""
    return run_command(
        "pytest -m 'not slow' -x --tb=line",
        "Quick Smoke Tests"
    )


def run_parallel_tests():
    """Run tests in parallel"""
    return run_command(
        "pytest -n auto test_hardware_system.py test_integration.py",
        "Parallel Test Execution"
    )


def run_with_html_report():
    """Run tests and generate HTML report"""
    success = run_command(
        "pytest test_hardware_system.py test_integration.py --html=test_report.html --self-contained-html",
        "Tests with HTML Report"
    )
    
    if success:
        print("\n📄 Test report generated: test_report.html")
    
    return success


def check_code_quality():
    """Run code quality checks"""
    print("\n🔍 Running code quality checks...\n")
    
    checks = [
        ("black --check *.py", "Black formatting"),
        ("isort --check-only *.py", "Import sorting"),
    ]
    
    all_passed = True
    for cmd, description in checks:
        if not run_command(cmd, description):
            all_passed = False
    
    return all_passed


def run_continuous_tests():
    """Run tests continuously on file changes"""
    print("\n👀 Watching for file changes... (Press Ctrl+C to stop)\n")
    try:
        subprocess.run("pytest-watch", shell=True)
    except KeyboardInterrupt:
        print("\n\nStopped watching for changes")


def list_tests():
    """List all available tests"""
    return run_command(
        "pytest --collect-only -q",
        "Available Tests"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Test Runner for Hardware Control System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --all              # Run all tests
  python run_tests.py --unit             # Run unit tests only
  python run_tests.py --integration      # Run integration tests
  python run_tests.py --coverage         # Run with coverage report
  python run_tests.py --module motor     # Run motor-related tests
  python run_tests.py --quick            # Run quick smoke tests
  python run_tests.py --safety           # Run safety-critical tests
        """
    )
    
    parser.add_argument('--all', action='store_true',
                       help='Run complete test suite')
    parser.add_argument('--unit', action='store_true',
                       help='Run unit tests only')
    parser.add_argument('--integration', action='store_true',
                       help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true',
                       help='Run tests with coverage report')
    parser.add_argument('--safety', action='store_true',
                       help='Run safety-critical tests')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick smoke tests')
    parser.add_argument('--parallel', action='store_true',
                       help='Run tests in parallel')
    parser.add_argument('--html', action='store_true',
                       help='Generate HTML test report')
    parser.add_argument('--quality', action='store_true',
                       help='Run code quality checks')
    parser.add_argument('--watch', action='store_true',
                       help='Run tests continuously on file changes')
    parser.add_argument('--list', action='store_true',
                       help='List all available tests')
    parser.add_argument('--module', type=str, metavar='NAME',
                       help='Run tests for specific module')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    results = []
    
    if args.all:
        results.append(run_all_tests())
    
    if args.unit:
        results.append(run_unit_tests())
    
    if args.integration:
        results.append(run_integration_tests())
    
    if args.coverage:
        results.append(run_with_coverage())
    
    if args.safety:
        results.append(run_safety_tests())
    
    if args.quick:
        results.append(run_quick_tests())
    
    if args.parallel:
        results.append(run_parallel_tests())
    
    if args.html:
        results.append(run_with_html_report())
    
    if args.quality:
        results.append(check_code_quality())
    
    if args.watch:
        run_continuous_tests()
        return 0
    
    if args.list:
        list_tests()
        return 0
    
    if args.module:
        results.append(run_specific_module(args.module))
    
    # Print summary
    if results:
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        if all(results):
            print("\n✅ All test suites PASSED")
            return 0
        else:
            print("\n❌ Some test suites FAILED")
            return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
