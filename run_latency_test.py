#!/usr/bin/env python3
"""
End-to-End Latency Test Runner

This script coordinates both Python and C++ latency tests to provide comprehensive
end-to-end latency measurement for the pairs trading system.
"""

import subprocess
import time
import sys
import os
import signal
import threading
import platform
from typing import Optional

def build_cpp_test():
    """Build the C++ latency test using platform-appropriate commands."""
    print("Building C++ latency test...")
    
    try:
        # Create build directory
        os.makedirs("cpp/build", exist_ok=True)
        
        # Configure with cmake
        print("  Configuring with CMake...")
        config_result = subprocess.run(
            ["cmake", ".."],
            cwd="cpp/build",
            capture_output=True,
            text=True
        )
        
        if config_result.returncode != 0:
            print("Failed to configure C++ test")
            print(config_result.stderr)
            return False
        
        # Build the target
        print("  Building latency_measurement_test...")
        build_result = subprocess.run(
            ["cmake", "--build", ".", "--config", "Release", "--target", "latency_measurement_test"],
            cwd="cpp/build",
            capture_output=True,
            text=True
        )
        
        if build_result.returncode != 0:
            print("Failed to build C++ test")
            print(build_result.stderr)
            return False
        
        # Check if executable exists
        exe_path = "cpp/build/Release/latency_measurement_test.exe"
        if not os.path.exists(exe_path):
            print(f"C++ test executable not found at {exe_path}")
            return False
        
        print("C++ test built successfully")
        return True
        
    except Exception as e:
        print(f"Build error: {e}")
        return False

def run_python_latency_test(num_signals: int = 1000, delay_ms: float = 1.0, port: int = 5555):
    """Run the Python latency test."""
    print(f"Starting Python latency test...")
    print(f"   Signals: {num_signals}")
    print(f"   Delay: {delay_ms}ms")
    print(f"   Port: {port}")
    
    try:
        # Run the Python latency test
        cmd = [
            sys.executable, 
            "tests/latency_measurement_test.py",
            "--signals", str(num_signals),
            "--delay", str(delay_ms),
            "--port", str(port)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("Python latency test completed successfully")
            print(result.stdout)
        else:
            print("Python latency test failed")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("Python latency test timed out")
        return False
    except Exception as e:
        print(f"Python latency test error: {e}")
        return False
    
    return True

def run_cpp_latency_test(port: int = 5555, duration_seconds: int = 30):
    """Run the C++ latency test."""
    print(f"Starting C++ latency test...")
    print(f"   Port: {port}")
    print(f"   Duration: {duration_seconds} seconds")
    
    try:
        # Build the C++ test first
        if not build_cpp_test():
            return False
        
        # Run the C++ test
        cpp_test_path = "cpp/build/Release/latency_measurement_test.exe"
        cmd = [cpp_test_path, str(port), str(duration_seconds)]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration_seconds + 60)
        
        if result.returncode == 0:
            print("C++ latency test completed successfully")
            print(result.stdout)
        else:
            print("C++ latency test failed")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("C++ latency test timed out")
        return False
    except Exception as e:
        print(f"C++ latency test error: {e}")
        return False
    
    return True

def run_combined_latency_test(num_signals: int = 1000, delay_ms: float = 1.0, port: int = 5555):
    """Run both Python and C++ tests simultaneously for end-to-end measurement."""
    print("Starting Combined End-to-End Latency Test")
    print("=" * 60)
    print(f"   Total Signals: {num_signals}")
    print(f"   Signal Delay: {delay_ms}ms")
    print(f"   ZMQ Port: {port}")
    print(f"   Test Duration: ~{num_signals * delay_ms / 1000 + 10} seconds")
    print("=" * 60)
    
    # Calculate test duration
    test_duration = int(num_signals * delay_ms / 1000) + 10
    
    # Build C++ test first
    print("\nBuilding C++ test...")
    if not build_cpp_test():
        print("Failed to build C++ test - running Python test only")
        return run_python_latency_test(num_signals, delay_ms, port)
    
    # Start C++ test in background
    print("\nStarting C++ receiver...")
    cpp_process = None
    
    try:
        # Start C++ test
        cpp_test_path = "cpp/build/Release/latency_measurement_test.exe"
        cpp_process = subprocess.Popen(
            [cpp_test_path, str(port), str(test_duration)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for C++ to start
        time.sleep(2)
        
        # Start Python test
        print("Starting Python sender...")
        python_cmd = [
            sys.executable, 
            "tests/latency_measurement_test.py",
            "--signals", str(num_signals),
            "--delay", str(delay_ms),
            "--port", str(port)
        ]
        
        python_process = subprocess.Popen(
            python_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for Python test to complete
        print("Waiting for tests to complete...")
        python_stdout, python_stderr = python_process.communicate(timeout=test_duration + 60)
        
        if python_process.returncode != 0:
            print("Python test failed")
            print(python_stderr)
            return False
        
        # Wait for C++ test to complete
        cpp_stdout, cpp_stderr = cpp_process.communicate(timeout=30)
        
        if cpp_process.returncode != 0:
            print("C++ test failed")
            print(cpp_stderr)
            return False
        
        # Print results
        print("\n" + "="*60)
        print("COMBINED TEST RESULTS")
        print("="*60)
        
        print("\nPython Test Output:")
        print("-" * 30)
        print(python_stdout)
        
        print("\nC++ Test Output:")
        print("-" * 30)
        print(cpp_stdout)
        
        print("\nCombined test completed successfully!")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("Test timed out")
        return False
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False
    finally:
        # Cleanup
        if cpp_process:
            try:
                cpp_process.terminate()
                cpp_process.wait(timeout=5)
            except:
                cpp_process.kill()

def print_usage():
    """Print usage information."""
    print("""
🚀 End-to-End Latency Test Runner

Usage:
  python run_latency_test.py [OPTIONS]

Options:
  --python-only          Run only Python latency test
  --cpp-only            Run only C++ latency test  
  --combined            Run both tests simultaneously (default)
  --signals N           Number of signals to send (default: 1000)
  --delay MS            Delay between signals in milliseconds (default: 1.0)
  --port PORT           ZMQ port to use (default: 5555)
  --help                Show this help message

Examples:
  # Run combined test with default settings
  python run_latency_test.py

  # Run with custom parameters
  python run_latency_test.py --signals 500 --delay 2.0 --port 5556

  # Run only Python test
  python run_latency_test.py --python-only

  # Run only C++ test
  python run_latency_test.py --cpp-only
""")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="End-to-End Latency Test Runner")
    parser.add_argument("--python-only", action="store_true", help="Run only Python test")
    parser.add_argument("--cpp-only", action="store_true", help="Run only C++ test")
    parser.add_argument("--combined", action="store_true", help="Run both tests (default)")
    parser.add_argument("--signals", type=int, default=1000, help="Number of signals")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between signals (ms)")
    parser.add_argument("--port", type=int, default=5555, help="ZMQ port")
    
    args = parser.parse_args()
    
    # Determine test mode
    if args.python_only:
        mode = "python"
    elif args.cpp_only:
        mode = "cpp"
    else:
        mode = "combined"
    
    print("End-to-End Latency Test Runner")
    print(f"   Mode: {mode.title()}")
    print(f"   Signals: {args.signals}")
    print(f"   Delay: {args.delay}ms")
    print(f"   Port: {args.port}")
    
    success = False
    
    try:
        if mode == "python":
            success = run_python_latency_test(args.signals, args.delay, args.port)
        elif mode == "cpp":
            success = run_cpp_latency_test(args.port, int(args.signals * args.delay / 1000) + 10)
        else:  # combined
            success = run_combined_latency_test(args.signals, args.delay, args.port)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        success = False
    except Exception as e:
        print(f"Test failed with error: {e}")
        success = False
    
    if success:
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 