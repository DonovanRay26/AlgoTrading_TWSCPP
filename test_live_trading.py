#!/usr/bin/env python3
"""
Live Trading Test Script
Tests the complete pairs trading system end-to-end including order execution.
"""

import subprocess
import time
import threading
import signal
import sys
import os
import zmq
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class LiveTradingTester:
    def __init__(self):
        self.python_proc = None
        self.cpp_proc = None
        self.running = True
        self.test_results = {
            'long_spread_test': False,
            'short_spread_test': False,
            'order_execution': False,
            'market_data': False
        }
        
        # ZMQ subscriber for monitoring signals
        self.context = zmq.Context()
        self.subscriber = None
        
        # Test parameters
        self.test_duration = 120  # 2 minutes
        self.signal_count = 0
        self.order_count = 0
        
    def setup_zmq_monitoring(self):
        """Setup ZMQ subscriber to monitor signals and orders."""
        try:
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect("tcp://localhost:5555")
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            self.subscriber.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            print("ZMQ monitoring setup complete")
            return True
        except Exception as e:
            print(f"Failed to setup ZMQ monitoring: {e}")
            return False
    
    def start_trading_system(self):
        """Start both Python and C++ trading engines."""
        print("🚀 Starting trading system...")
        
        try:
            # Start the main trading system
            self.python_proc = subprocess.Popen(
                [sys.executable, 'run_trading_system.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            print("Trading system started")
            return True
            
        except Exception as e:
            print(f"Failed to start trading system: {e}")
            return False
    
    def monitor_signals_and_orders(self):
        """Monitor ZMQ messages for signals and orders."""
        print("📡 Monitoring signals and orders...")
        
        start_time = time.time()
        
        while self.running and (time.time() - start_time) < self.test_duration:
            try:
                message = self.subscriber.recv_string()
                data = json.loads(message)
                
                message_type = data.get('message_type', '')
                
                if message_type == 'TRADE_SIGNAL':
                    self.signal_count += 1
                    signal_type = data.get('signal_type', '')
                    pair_name = data.get('pair_name', '')
                    z_score = data.get('z_score', 0)
                    
                    print(f"Signal #{self.signal_count}: {signal_type} for {pair_name} (Z-Score: {z_score:.3f})")
                    
                    if signal_type == 'ENTER_LONG_SPREAD':
                        self.test_results['long_spread_test'] = True
                    elif signal_type == 'ENTER_SHORT_SPREAD':
                        self.test_results['short_spread_test'] = True
                
                elif message_type == 'POSITION_UPDATE':
                    self.order_count += 1
                    position_type = data.get('current_position', '')
                    shares_a = data.get('shares_a', 0)
                    shares_b = data.get('shares_b', 0)
                    
                    print(f"Order #{self.order_count}: {position_type} - A: {shares_a}, B: {shares_b}")
                    self.test_results['order_execution'] = True
                
                elif message_type == 'SYSTEM_STATUS':
                    status = data.get('status', '')
                    component = data.get('component', '')
                    print(f"System Status: {component} - {status}")
                
            except zmq.Again:
                # Timeout - continue monitoring
                continue
            except Exception as e:
                print(f"Error monitoring messages: {e}")
                continue
    
    def check_market_data_flow(self):
        """Check if market data is flowing properly."""
        print("Checking market data flow...")
        
        # Wait for initial market data
        time.sleep(10)
        
        # Check if we're receiving price updates
        if self.signal_count > 0:
            self.test_results['market_data'] = True
            print("Market data is flowing")
        else:
            print("No signals received - market data may not be flowing")
    
    def generate_test_signals(self):
        """Generate test signals by modifying strategy parameters temporarily."""
        print("Generating test signals...")
        
        # Create a test signal generator
        test_signals = [
            {
                'signal_type': 'ENTER_LONG_SPREAD',
                'pair_name': 'EWA_EWC',
                'symbol_a': 'EWA',
                'symbol_b': 'EWC',
                'z_score': -2.5,  # Strong long signal
                'hedge_ratio': 1.23,
                'confidence': 0.85,
                'shares_a': 100,
                'shares_b': -123
            },
            {
                'signal_type': 'EXIT_POSITION',
                'pair_name': 'EWA_EWC',
                'symbol_a': 'EWA',
                'symbol_b': 'EWC',
                'z_score': 0.1,
                'hedge_ratio': 1.23,
                'confidence': 0.85,
                'shares_a': 0,
                'shares_b': 0
            },
            {
                'signal_type': 'ENTER_SHORT_SPREAD',
                'pair_name': 'EWA_EWC',
                'symbol_a': 'EWA',
                'symbol_b': 'EWC',
                'z_score': 2.5,  # Strong short signal
                'hedge_ratio': 1.23,
                'confidence': 0.85,
                'shares_a': -100,
                'shares_b': 123
            },
            {
                'signal_type': 'EXIT_POSITION',
                'pair_name': 'EWA_EWC',
                'symbol_a': 'EWA',
                'symbol_b': 'EWC',
                'z_score': -0.1,
                'hedge_ratio': 1.23,
                'confidence': 0.85,
                'shares_a': 0,
                'shares_b': 0
            }
        ]
        
        # Send test signals via ZMQ
        publisher = self.context.socket(zmq.PUB)
        publisher.bind("tcp://*:5556")  # Use different port for test signals
        time.sleep(0.1)  # Allow binding
        
        for i, test_signal in enumerate(test_signals):
            print(f"Sending test signal {i+1}: {test_signal['signal_type']}")
            
            # Create proper trade signal format
            trade_signal = {
                'message_type': 'TRADE_SIGNAL',
                'message_id': f'test_{i}_{int(time.time())}',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'pair_name': test_signal['pair_name'],
                'symbol_a': test_signal['symbol_a'],
                'symbol_b': test_signal['symbol_b'],
                'signal_type': test_signal['signal_type'],
                'z_score': test_signal['z_score'],
                'hedge_ratio': test_signal['hedge_ratio'],
                'confidence': test_signal['confidence'],
                'position_size': 100,
                'shares_a': test_signal['shares_a'],
                'shares_b': test_signal['shares_b'],
                'volatility': 0.15,
                'correlation': 0.85
            }
            
            publisher.send_string(json.dumps(trade_signal))
            time.sleep(2)  # Wait between signals
        
        publisher.close()
    
    def run_test(self):
        """Run the complete live trading test."""
        print("Starting Live Trading Test")
        print("=" * 50)
        
        try:
            # Setup monitoring
            if not self.setup_zmq_monitoring():
                return False
            
            # Start trading system
            if not self.start_trading_system():
                return False
            
            # Wait for system to initialize
            print("Waiting for system initialization...")
            time.sleep(15)
            
            # Start monitoring in background
            monitor_thread = threading.Thread(target=self.monitor_signals_and_orders)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Check market data flow
            self.check_market_data_flow()
            
            # Generate test signals
            self.generate_test_signals()
            
            # Wait for test completion
            print(f"Running test for {self.test_duration} seconds...")
            time.sleep(self.test_duration)
            
            # Stop monitoring
            self.running = False
            
            # Wait for monitoring thread to finish
            monitor_thread.join(timeout=5)
            
            return True
            
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            return False
        except Exception as e:
            print(f"Test failed: {e}")
            return False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        print("Cleaning up...")
        
        # Stop monitoring
        self.running = False
        
        # Close ZMQ connections
        if self.subscriber:
            self.subscriber.close()
        self.context.term()
        
        # Stop trading system
        if self.python_proc:
            print("Stopping trading system...")
            self.python_proc.terminate()
            try:
                self.python_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.python_proc.kill()
    
    def print_results(self):
        """Print test results."""
        print("\n" + "=" * 50)
        print("LIVE TRADING TEST RESULTS")
        print("=" * 50)
        
        print(f"Market Data Flow: {'PASS' if self.test_results['market_data'] else 'FAIL'}")
        print(f"Long Spread Test: {'PASS' if self.test_results['long_spread_test'] else 'FAIL'}")
        print(f"Short Spread Test: {'PASS' if self.test_results['short_spread_test'] else 'FAIL'}")
        print(f"Order Execution: {'PASS' if self.test_results['order_execution'] else 'FAIL'}")
        
        print(f"\nStatistics:")
        print(f"   Signals Generated: {self.signal_count}")
        print(f"   Orders Executed: {self.order_count}")
        
        # Overall result
        all_passed = all(self.test_results.values())
        print(f"\nOverall Result: {'PASS' if all_passed else 'FAIL'}")
        
        if all_passed:
            print("All tests passed! Your trading system is working correctly.")
        else:
            print("Some tests failed. Check the logs for details.")
        
        return all_passed

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print(f"\nReceived signal {signum}, stopping test...")
    if hasattr(signal_handler, 'tester'):
        signal_handler.tester.running = False

def main():
    """Main test function."""
    print("Live Trading System Test")
    print("This test will:")
    print("1. Start the complete trading system")
    print("2. Monitor market data flow")
    print("3. Generate test long and short spread signals")
    print("4. Verify order execution")
    print("5. Clean up and report results")
    print()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run tester
    tester = LiveTradingTester()
    signal_handler.tester = tester
    
    try:
        success = tester.run_test()
        tester.print_results()
        
        if success:
            print("\nTest completed successfully!")
            return 0
        else:
            print("\nTest failed!")
            return 1
            
    except Exception as e:
        print(f"\nTest crashed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 