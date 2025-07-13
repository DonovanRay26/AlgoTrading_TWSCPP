#!/usr/bin/env python3
"""
Python test runner for the pairs trading system.
Runs all Python tests and provides a comprehensive report.
"""

import unittest
import sys
import os
import time
from datetime import datetime

# Add the python directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'python'))

def run_test_suite():
    """Run all Python tests and return results."""
    print("Running Python Tests for Pairs Trading System")
    print("=" * 60)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(__file__)
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    return result, end_time - start_time

def print_summary(result, duration):
    """Print test summary."""
    print("\n" + "=" * 60)
    print("PYTHON TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total_tests - failures - errors
    success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Duration: {duration:.2f} seconds")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if failures > 0:
        print(f"\nFAILURES ({failures}):")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors > 0:
        print(f"\nERRORS ({errors}):")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback.split('Exception:')[-1].strip()}")
    
    print("\n" + "=" * 60)
    
    if failures == 0 and errors == 0:
        print("ALL PYTHON TESTS PASSED!")
        print("Python components are working correctly")
        print("Ready for integration with C++ components")
    else:
        print("SOME TESTS FAILED")
        print("Please fix the issues before proceeding")
    
    print("=" * 60)
    
    return failures == 0 and errors == 0

def check_dependencies():
    """Check if required dependencies are available."""
    print("🔍 Checking Python Dependencies...")
    
    required_packages = [
        'numpy', 'pandas', 'zmq', 'yaml', 'unittest',
        'pykalman', 'statsmodels', 'yfinance'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  {package}")
        except ImportError:
            print(f"  {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Please install missing packages:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("All dependencies available")
    return True

def main():
    """Main test runner function."""
    print(f"Python Test Runner - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check dependencies first
    if not check_dependencies():
        print("\nCannot run tests due to missing dependencies")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # Run tests
    try:
        result, duration = run_test_suite()
        success = print_summary(result, duration)
        
        if success:
            print("\nNEXT STEPS:")
            print("1. Python components tested successfully")
            print("2. Ready for integration testing with C++")
            print("3. Can proceed with live trading setup")
            sys.exit(0)
        else:
            print("\nNEXT STEPS:")
            print("1. Fix failing Python tests")
            print("2. Re-run tests after fixes")
            print("3. Proceed only after all tests pass")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nTest runner error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 