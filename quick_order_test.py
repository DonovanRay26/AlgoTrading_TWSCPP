#!/usr/bin/env python3
"""
Quick Order Test Script
Directly tests order execution by sending test signals to the C++ engine.
"""

import zmq
import json
import time
import subprocess
import sys
import signal
from datetime import datetime

class QuickOrderTester:
    def __init__(self):
        self.context = zmq.Context()
        self.publisher = None
        self.subscriber = None
        self.trading_system_proc = None
        self.test_results = {
            'long_spread_placed': False,
            'short_spread_placed': False,
            'orders_executed': False
        }
        
    def start_trading_system(self):
        """Start the trading system in background."""
        print("🚀 Starting trading system...")
        
        try:
            self.trading_system_proc = subprocess.Popen(
                [sys.executable, 'run_trading_system.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Wait for system to start
            time.sleep(10)
            print("✅ Trading system started")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start trading system: {e}")
            return False
    
    def setup_zmq(self):
        """Setup ZMQ publisher and subscriber."""
        try:
            # Publisher for sending test signals
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind("tcp://*:5556")
            time.sleep(0.1)  # Allow binding
            
            # Subscriber for monitoring responses
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect("tcp://localhost:5555")
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            self.subscriber.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
            
            print("✅ ZMQ setup complete")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup ZMQ: {e}")
            return False
    
    def send_test_signal(self, signal_type, shares_a, shares_b, z_score=2.5):
        """Send a test signal to the order engine."""
        test_signal = {
            'message_type': 'TRADE_SIGNAL',
            'message_id': f'quick_test_{int(time.time())}',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'pair_name': 'EWA_EWC',
            'symbol_a': 'EWA',
            'symbol_b': 'EWC',
            'signal_type': signal_type,
            'z_score': z_score,
            'hedge_ratio': 1.23,
            'confidence': 0.95,  # High confidence to ensure execution
            'position_size': 100,
            'shares_a': shares_a,
            'shares_b': shares_b,
            'volatility': 0.15,
            'correlation': 0.85
        }
        
        print(f"📤 Sending {signal_type} signal: A={shares_a}, B={shares_b}")
        self.publisher.send_string(json.dumps(test_signal))
    
    def monitor_responses(self, timeout=10):
        """Monitor responses from the order engine."""
        print("📡 Monitoring order responses...")
        
        start_time = time.time()
        responses = []
        
        while (time.time() - start_time) < timeout:
            try:
                message = self.subscriber.recv_string()
                data = json.loads(message)
                responses.append(data)
                
                message_type = data.get('message_type', '')
                
                if message_type == 'POSITION_UPDATE':
                    shares_a = data.get('shares_a', 0)
                    shares_b = data.get('shares_b', 0)
                    position_type = data.get('current_position', '')
                    
                    print(f"📈 Position Update: {position_type} - A: {shares_a}, B: {shares_b}")
                    self.test_results['orders_executed'] = True
                    
                    if shares_a > 0 and shares_b < 0:
                        self.test_results['long_spread_placed'] = True
                    elif shares_a < 0 and shares_b > 0:
                        self.test_results['short_spread_placed'] = True
                
                elif message_type == 'SYSTEM_STATUS':
                    status = data.get('status', '')
                    component = data.get('component', '')
                    print(f"🔧 {component}: {status}")
                
                elif message_type == 'ERROR_MESSAGE':
                    error_msg = data.get('error_message', '')
                    print(f"❌ Error: {error_msg}")
                
            except zmq.Again:
                # Timeout - continue monitoring
                continue
            except Exception as e:
                print(f"⚠️ Error reading message: {e}")
                continue
        
        return responses
    
    def run_quick_test(self):
        """Run the quick order test."""
        print("🧪 Quick Order Test")
        print("=" * 40)
        
        try:
            # Setup
            if not self.setup_zmq():
                return False
            
            if not self.start_trading_system():
                return False
            
            # Wait for system to be ready
            print("⏳ Waiting for system to be ready...")
            time.sleep(5)
            
            # Test 1: Long Spread
            print("\n🧪 Test 1: Long Spread (Long EWA, Short EWC)")
            self.send_test_signal('ENTER_LONG_SPREAD', 100, -123, -2.5)
            responses = self.monitor_responses(timeout=15)
            
            # Wait a moment
            time.sleep(3)
            
            # Test 2: Exit Long Spread
            print("\n🧪 Test 2: Exit Long Spread")
            self.send_test_signal('EXIT_POSITION', 0, 0, 0.1)
            responses.extend(self.monitor_responses(timeout=10))
            
            # Wait a moment
            time.sleep(3)
            
            # Test 3: Short Spread
            print("\n🧪 Test 3: Short Spread (Short EWA, Long EWC)")
            self.send_test_signal('ENTER_SHORT_SPREAD', -100, 123, 2.5)
            responses.extend(self.monitor_responses(timeout=15))
            
            # Wait a moment
            time.sleep(3)
            
            # Test 4: Exit Short Spread
            print("\n🧪 Test 4: Exit Short Spread")
            self.send_test_signal('EXIT_POSITION', 0, 0, -0.1)
            responses.extend(self.monitor_responses(timeout=10))
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...")
        
        # Close ZMQ connections
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        self.context.term()
        
        # Stop trading system
        if self.trading_system_proc:
            print("🛑 Stopping trading system...")
            self.trading_system_proc.terminate()
            try:
                self.trading_system_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.trading_system_proc.kill()
    
    def print_results(self):
        """Print test results."""
        print("\n" + "=" * 40)
        print("📊 QUICK ORDER TEST RESULTS")
        print("=" * 40)
        
        print(f"✅ Long Spread Placed: {'PASS' if self.test_results['long_spread_placed'] else 'FAIL'}")
        print(f"✅ Short Spread Placed: {'PASS' if self.test_results['short_spread_placed'] else 'FAIL'}")
        print(f"✅ Orders Executed: {'PASS' if self.test_results['orders_executed'] else 'FAIL'}")
        
        # Overall result
        all_passed = all(self.test_results.values())
        print(f"\n🎯 Overall Result: {'PASS' if all_passed else 'FAIL'}")
        
        if all_passed:
            print("🎉 All order tests passed! Order execution is working.")
        else:
            print("⚠️ Some order tests failed. Check TWS and account settings.")
        
        return all_passed

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print(f"\n⚠️ Received signal {signum}, stopping test...")
    if hasattr(signal_handler, 'tester'):
        signal_handler.tester.cleanup()

def main():
    """Main test function."""
    print("🧪 Quick Order Execution Test")
    print("This test will:")
    print("1. Start the trading system")
    print("2. Send test long spread signal")
    print("3. Send test short spread signal")
    print("4. Verify order execution")
    print("5. Clean up")
    print()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run tester
    tester = QuickOrderTester()
    signal_handler.tester = tester
    
    try:
        success = tester.run_quick_test()
        tester.print_results()
        
        if success:
            print("\n🎉 Quick test completed!")
            return 0
        else:
            print("\n❌ Quick test failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 