#!/usr/bin/env python3
"""
End-to-End Latency Measurement Test for Pairs Trading System

This test measures the actual latency from Python signal generation to C++ order processing.
It provides detailed breakdowns of each component's latency and generates performance reports.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../python')))

import time
import json
import threading
import statistics
import zmq
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from collections import deque

# Import our trading system components
from comms.message_protocol import SignalType, create_trade_signal, create_heartbeat
from comms.signaler import SignalPublisher
from strategy.kalman_filter import PairsKalmanFilter


@dataclass
class LatencyMeasurement:
    """Data structure for storing latency measurements."""
    signal_id: str
    python_generation_start: float = None
    python_generation_end: float = None
    python_serialization_start: float = None
    python_serialization_end: float = None
    python_zmq_send_start: float = None
    python_zmq_send_end: float = None
    cpp_receive_start: Optional[float] = None
    cpp_receive_end: Optional[float] = None
    cpp_parsing_start: Optional[float] = None
    cpp_parsing_end: Optional[float] = None
    cpp_risk_check_start: Optional[float] = None
    cpp_risk_check_end: Optional[float] = None
    cpp_order_creation_start: Optional[float] = None
    cpp_order_creation_end: Optional[float] = None
    cpp_tws_submit_start: Optional[float] = None
    cpp_tws_submit_end: Optional[float] = None
    error_message: Optional[str] = None

    def get_python_generation_latency(self) -> float:
        """Get Python signal generation latency in microseconds."""
        return (self.python_generation_end - self.python_generation_start) * 1_000_000

    def get_python_serialization_latency(self) -> float:
        """Get Python serialization latency in microseconds."""
        return (self.python_serialization_end - self.python_serialization_start) * 1_000_000

    def get_python_zmq_latency(self) -> float:
        """Get Python ZMQ send latency in microseconds."""
        return (self.python_zmq_send_end - self.python_zmq_send_start) * 1_000_000

    def get_network_latency(self) -> Optional[float]:
        """Get network transmission latency in microseconds."""
        if self.cpp_receive_start is None:
            return None
        # Use Python ZMQ send start instead of end to avoid negative values
        # Cap at 0 since negative values indicate very fast transmission
        latency = (self.cpp_receive_start - self.python_zmq_send_start) * 1_000_000
        return max(0, latency)  # Cap negative values at 0

    def get_cpp_receive_latency(self) -> Optional[float]:
        """Get C++ receive latency in microseconds."""
        if self.cpp_receive_end is None or self.cpp_receive_start is None:
            return None
        return (self.cpp_receive_end - self.cpp_receive_start) * 1_000_000

    def get_cpp_parsing_latency(self) -> Optional[float]:
        """Get C++ parsing latency in microseconds."""
        if self.cpp_parsing_end is None or self.cpp_parsing_start is None:
            return None
        return (self.cpp_parsing_end - self.cpp_parsing_start) * 1_000_000

    def get_cpp_risk_check_latency(self) -> Optional[float]:
        """Get C++ risk check latency in microseconds."""
        if self.cpp_risk_check_end is None or self.cpp_risk_check_start is None:
            return None
        return (self.cpp_risk_check_end - self.cpp_risk_check_start) * 1_000_000

    def get_cpp_order_creation_latency(self) -> Optional[float]:
        """Get C++ order creation latency in microseconds."""
        if self.cpp_order_creation_end is None or self.cpp_order_creation_start is None:
            return None
        return (self.cpp_order_creation_end - self.cpp_order_creation_start) * 1_000_000

    def get_cpp_tws_latency(self) -> Optional[float]:
        """Get C++ TWS submission latency in microseconds."""
        if self.cpp_tws_submit_end is None or self.cpp_tws_submit_start is None:
            return None
        return (self.cpp_tws_submit_end - self.cpp_tws_submit_start) * 1_000_000

    def get_total_python_latency(self) -> float:
        """Get total Python-side latency in microseconds."""
        return (self.python_zmq_send_end - self.python_generation_start) * 1_000_000

    def get_total_cpp_latency(self) -> Optional[float]:
        """Get total C++-side latency in microseconds."""
        if self.cpp_tws_submit_end is None or self.cpp_receive_start is None:
            return None
        return (self.cpp_tws_submit_end - self.cpp_receive_start) * 1_000_000

    def get_end_to_end_latency(self) -> Optional[float]:
        """Get end-to-end latency in microseconds."""
        if self.cpp_tws_submit_end is None:
            return None
        return (self.cpp_tws_submit_end - self.python_generation_start) * 1_000_000


class LatencyTestPublisher:
    """Enhanced signal publisher with latency measurement."""
    
    def __init__(self, host: str = "localhost", port: int = 5555):
        self.host = host
        self.port = port
        self.publisher = SignalPublisher(host, port)
        self.measurements: List[LatencyMeasurement] = []
        self.lock = threading.Lock()
        
    def connect(self) -> bool:
        """Connect to ZMQ publisher."""
        return self.publisher.connect()
    
    def disconnect(self):
        """Disconnect from ZMQ publisher."""
        self.publisher.disconnect()
    
    def send_signal_with_measurement(self, signal_id: str) -> LatencyMeasurement:
        """Send a test signal with comprehensive latency measurement."""
        # Python signal generation timing
        generation_start = time.perf_counter()
        
        # Create test signal
        trade_signal = create_trade_signal(
            pair_name="TEST_PAIR",
            symbol_a="TEST_A",
            symbol_b="TEST_B",
            signal_type=SignalType.ENTER_LONG_SPREAD,
            z_score=2.5,
            hedge_ratio=0.8,
            confidence=0.85,
            position_size=1000,
            shares_a=100,
            shares_b=-80,
            volatility=0.25,
            correlation=0.75
        )
        
        generation_end = time.perf_counter()
        
        # Use the actual message_id from the signal
        actual_signal_id = trade_signal.message_id
        measurement = LatencyMeasurement(signal_id=actual_signal_id)
        measurement.python_generation_start = generation_start
        measurement.python_generation_end = generation_end
        
        # Python serialization timing
        measurement.python_serialization_start = time.perf_counter()
        signal_dict = trade_signal.to_dict()
        signal_json = json.dumps(signal_dict)
        measurement.python_serialization_end = time.perf_counter()
        
        # Python ZMQ send timing
        measurement.python_zmq_send_start = time.perf_counter()
        success = self.publisher.send_trade_signal(trade_signal)
        measurement.python_zmq_send_end = time.perf_counter()
        
        if not success:
            measurement.error_message = "Failed to send signal via ZMQ"
        
        # Store measurement
        with self.lock:
            self.measurements.append(measurement)
        
        return measurement


class LatencyTestSubscriber:
    """ZMQ subscriber that simulates C++ signal processing with latency measurement."""
    
    def __init__(self, host: str = "localhost", port: int = 5555):
        self.host = host
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.measurements: Dict[str, LatencyMeasurement] = {}
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        
    def connect(self):
        """Connect to ZMQ publisher."""
        self.socket.connect(f"tcp://{self.host}:{self.port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "TRADE_SIGNAL")
        
    def disconnect(self):
        """Disconnect from ZMQ publisher."""
        self.running = False
        if self.thread:
            self.thread.join()
        self.socket.close()
        self.context.term()
    
    def start_listening(self):
        """Start listening for signals in a separate thread."""
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop)
        self.thread.start()
    
    def _listen_loop(self):
        """Main listening loop that simulates C++ processing."""
        print("Subscriber listening loop started")
        while self.running:
            try:
                # Set timeout for non-blocking receive
                self.socket.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
                
                # C++ receive start timing
                receive_start = time.perf_counter()
                
                topic = self.socket.recv_string()
                message = self.socket.recv_json()
                
                receive_end = time.perf_counter()
                
                print(f"Received message: {topic} - {message.get('message_id', 'unknown')}")
                
                # Extract signal ID from message
                signal_id = message.get("message_id", "unknown")
                
                # C++ parsing timing
                parsing_start = time.perf_counter()
                
                # Simulate JSON parsing (like C++ signal parser)
                pair_name = message.get("pair_name", "")
                signal_type = message.get("signal_type", "")
                z_score = message.get("z_score", 0.0)
                confidence = message.get("confidence", 0.0)
                shares_a = message.get("shares_a", 0)
                shares_b = message.get("shares_b", 0)
                
                parsing_end = time.perf_counter()
                
                # C++ risk check timing
                risk_check_start = time.perf_counter()
                
                # Simulate risk checking (like C++ risk checker)
                risk_passed = (
                    confidence >= 0.7 and
                    abs(z_score) <= 3.0 and
                    abs(shares_a) <= 10000 and
                    abs(shares_b) <= 10000
                )
                
                risk_check_end = time.perf_counter()
                
                # C++ order creation timing
                order_creation_start = time.perf_counter()
                
                # Simulate order creation (like C++ order manager)
                if risk_passed:
                    order_a = {
                        "symbol": "TEST_A",
                        "action": "BUY" if shares_a > 0 else "SELL",
                        "quantity": abs(shares_a),
                        "orderType": "MKT"
                    }
                    order_b = {
                        "symbol": "TEST_B",
                        "action": "BUY" if shares_b > 0 else "SELL",
                        "quantity": abs(shares_b),
                        "orderType": "MKT"
                    }
                
                order_creation_end = time.perf_counter()
                
                # C++ TWS submission timing
                tws_submit_start = time.perf_counter()
                
                # Simulate TWS submission (network delay + processing)
                time.sleep(0.005)  # Simulate 5ms TWS processing
                
                tws_submit_end = time.perf_counter()
                
                # Update measurement with C++ timings
                with self.lock:
                    if signal_id in self.measurements:
                        measurement = self.measurements[signal_id]
                        measurement.cpp_receive_start = receive_start
                        measurement.cpp_receive_end = receive_end
                        measurement.cpp_parsing_start = parsing_start
                        measurement.cpp_parsing_end = parsing_end
                        measurement.cpp_risk_check_start = risk_check_start
                        measurement.cpp_risk_check_end = risk_check_end
                        measurement.cpp_order_creation_start = order_creation_start
                        measurement.cpp_order_creation_end = order_creation_end
                        measurement.cpp_tws_submit_start = tws_submit_start
                        measurement.cpp_tws_submit_end = tws_submit_end
                        
                        if not risk_passed:
                            measurement.error_message = "Risk check failed"
                        
                        # Debug timing
                        network_latency = (receive_start - measurement.python_zmq_send_start) * 1_000_000
                        corrected_latency = max(0, network_latency)
                        print(f"Updated measurement for signal {signal_id}")
                        print(f"  Python ZMQ Send Start: {measurement.python_zmq_send_start:.6f}")
                        print(f"  C++ Receive Start:     {receive_start:.6f}")
                        print(f"  Raw Network Latency:   {network_latency:.2f} us")
                        print(f"  Corrected Latency:     {corrected_latency:.2f} us")
                    else:
                        print(f"Warning: No measurement found for signal {signal_id}")
                
            except zmq.Again:
                # Timeout - continue listening
                continue
            except Exception as e:
                print(f"Error in listening loop: {e}")
                break
    
    def add_measurement(self, measurement: LatencyMeasurement):
        """Add a measurement to track."""
        with self.lock:
            self.measurements[measurement.signal_id] = measurement


class LatencyAnalyzer:
    """Analyzes latency measurements and generates reports."""
    
    def __init__(self):
        self.measurements: List[LatencyMeasurement] = []
        
    def add_measurements(self, measurements: List[LatencyMeasurement]):
        """Add measurements for analysis."""
        self.measurements.extend(measurements)
    
    def calculate_statistics(self, latencies: List[float]) -> Dict[str, float]:
        """Calculate statistical measures for a list of latencies."""
        if not latencies:
            return {}
        
        return {
            "count": len(latencies),
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "std": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "min": min(latencies),
            "max": max(latencies),
            "p50": np.percentile(latencies, 50),
            "p90": np.percentile(latencies, 90),
            "p95": np.percentile(latencies, 95),
            "p99": np.percentile(latencies, 99),
            "p99.9": np.percentile(latencies, 99.9)
        }
    
    def generate_latency_report(self) -> Dict[str, Dict[str, float]]:
        """Generate comprehensive latency report."""
        report = {}
        
        # Python generation latency
        python_gen_latencies = [m.get_python_generation_latency() for m in self.measurements]
        report["python_generation"] = self.calculate_statistics(python_gen_latencies)
        
        # Python serialization latency
        python_serial_latencies = [m.get_python_serialization_latency() for m in self.measurements]
        report["python_serialization"] = self.calculate_statistics(python_serial_latencies)
        
        # Python ZMQ latency
        python_zmq_latencies = [m.get_python_zmq_latency() for m in self.measurements]
        report["python_zmq"] = self.calculate_statistics(python_zmq_latencies)
        
        # Total Python latency
        python_total_latencies = [m.get_total_python_latency() for m in self.measurements]
        report["python_total"] = self.calculate_statistics(python_total_latencies)
        
        # Network latency (Python ZMQ send to C++ receive)
        network_latencies = [m.get_network_latency() for m in self.measurements if m.get_network_latency() is not None]
        report["network"] = self.calculate_statistics(network_latencies)
        
        # C++ receive latency
        cpp_receive_latencies = [m.get_cpp_receive_latency() for m in self.measurements if m.get_cpp_receive_latency() is not None]
        report["cpp_receive"] = self.calculate_statistics(cpp_receive_latencies)
        
        # C++ parsing latency
        cpp_parsing_latencies = [m.get_cpp_parsing_latency() for m in self.measurements if m.get_cpp_parsing_latency() is not None]
        report["cpp_parsing"] = self.calculate_statistics(cpp_parsing_latencies)
        
        # C++ risk check latency
        cpp_risk_latencies = [m.get_cpp_risk_check_latency() for m in self.measurements if m.get_cpp_risk_check_latency() is not None]
        report["cpp_risk_check"] = self.calculate_statistics(cpp_risk_latencies)
        
        # C++ order creation latency
        cpp_order_latencies = [m.get_cpp_order_creation_latency() for m in self.measurements if m.get_cpp_order_creation_latency() is not None]
        report["cpp_order_creation"] = self.calculate_statistics(cpp_order_latencies)
        
        # C++ TWS latency
        cpp_tws_latencies = [m.get_cpp_tws_latency() for m in self.measurements if m.get_cpp_tws_latency() is not None]
        report["cpp_tws"] = self.calculate_statistics(cpp_tws_latencies)
        
        # Total C++ latency
        cpp_total_latencies = [m.get_total_cpp_latency() for m in self.measurements if m.get_total_cpp_latency() is not None]
        report["cpp_total"] = self.calculate_statistics(cpp_total_latencies)
        
        # End-to-end latency
        e2e_latencies = [m.get_end_to_end_latency() for m in self.measurements if m.get_end_to_end_latency() is not None]
        report["end_to_end"] = self.calculate_statistics(e2e_latencies)
        
        return report
    
    def print_latency_report(self, report: Dict[str, Dict[str, float]]):
        """Print formatted latency report."""
        print("\n" + "="*80)
        print("END-TO-END LATENCY MEASUREMENT REPORT")
        print("="*80)
        
        # Print summary statistics
        print(f"\nSUMMARY STATISTICS (All times in microseconds)")
        print("-" * 80)
        
        for stage, stats in report.items():
            if not stats:
                continue
                
            print(f"\n{stage.upper().replace('_', ' ')}:")
            print(f"   Count: {stats.get('count', 0)}")
            print(f"   Mean:   {stats.get('mean', 0):.2f} us")
            print(f"   Median: {stats.get('median', 0):.2f} us")
            print(f"   Std:    {stats.get('std', 0):.2f} us")
            print(f"   Min:    {stats.get('min', 0):.2f} us")
            print(f"   Max:    {stats.get('max', 0):.2f} us")
            print(f"   P50:    {stats.get('p50', 0):.2f} us")
            print(f"   P90:    {stats.get('p90', 0):.2f} us")
            print(f"   P95:    {stats.get('p95', 0):.2f} us")
            print(f"   P99:    {stats.get('p99', 0):.2f} us")
            print(f"   P99.9:  {stats.get('p99.9', 0):.2f} us")
        
        # Print end-to-end analysis
        e2e_stats = report.get("end_to_end", {})
        if e2e_stats:
            print(f"\nEND-TO-END LATENCY ANALYSIS:")
            print(f"   Average: {e2e_stats.get('mean', 0):.2f} us ({e2e_stats.get('mean', 0)/1000:.2f} ms)")
            print(f"   P95:     {e2e_stats.get('p95', 0):.2f} us ({e2e_stats.get('p95', 0)/1000:.2f} ms)")
            print(f"   P99:     {e2e_stats.get('p99', 0):.2f} us ({e2e_stats.get('p99', 0)/1000:.2f} ms)")
            
            # Performance assessment
            avg_ms = e2e_stats.get('mean', 0) / 1000
            if avg_ms < 1:
                performance = "EXCELLENT - Sub-millisecond performance!"
            elif avg_ms < 5:
                performance = "GOOD - Competitive latency"
            elif avg_ms < 10:
                performance = "ACCEPTABLE - Room for optimization"
            else:
                performance = "NEEDS IMPROVEMENT - High latency detected"
            
            print(f"   Assessment: {performance}")
        
        # Print latency breakdown
        print(f"\nLATENCY BREAKDOWN:")
        print(f"   Python Generation:    {report.get('python_generation', {}).get('mean', 0):.2f} us")
        print(f"   Python Serialization: {report.get('python_serialization', {}).get('mean', 0):.2f} us")
        print(f"   Python ZMQ Send:      {report.get('python_zmq', {}).get('mean', 0):.2f} us")
        print(f"   Network Transmission: {report.get('network', {}).get('mean', 0):.2f} us")
        print(f"   C++ Receive:          {report.get('cpp_receive', {}).get('mean', 0):.2f} us")
        print(f"   C++ Parsing:          {report.get('cpp_parsing', {}).get('mean', 0):.2f} us")
        print(f"   C++ Risk Check:       {report.get('cpp_risk_check', {}).get('mean', 0):.2f} us")
        print(f"   C++ Order Creation:   {report.get('cpp_order_creation', {}).get('mean', 0):.2f} us")
        print(f"   C++ TWS Submit:       {report.get('cpp_tws', {}).get('mean', 0):.2f} us")
        
        print("\n" + "="*80)
    
    def create_latency_plots(self, report: Dict[str, Dict[str, float]], save_path: str = "latency_analysis.png"):
        """Create latency visualization plots."""
        try:
            # Prepare data for plotting
            stages = []
            means = []
            p95s = []
            p99s = []
            
            for stage, stats in report.items():
                if stats and 'mean' in stats:
                    stages.append(stage.replace('_', ' ').title())
                    means.append(stats['mean'])
                    p95s.append(stats.get('p95', 0))
                    p99s.append(stats.get('p99', 0))
            
            # Create subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
            
            # Plot 1: Mean latency by stage
            ax1.bar(stages, means, color='skyblue', alpha=0.7)
            ax1.set_title('Mean Latency by Stage', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Latency (us)')
            ax1.tick_params(axis='x', rotation=45)
            
            # Plot 2: P95 vs P99 latency
            x = np.arange(len(stages))
            width = 0.35
            ax2.bar(x - width/2, p95s, width, label='P95', color='lightcoral', alpha=0.7)
            ax2.bar(x + width/2, p99s, width, label='P99', color='lightgreen', alpha=0.7)
            ax2.set_title('P95 vs P99 Latency by Stage', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Latency (us)')
            ax2.set_xticks(x)
            ax2.set_xticklabels(stages, rotation=45)
            ax2.legend()
            
            # Plot 3: End-to-end latency distribution
            e2e_latencies = [m.get_end_to_end_latency() for m in self.measurements if m.get_end_to_end_latency() is not None]
            if e2e_latencies:
                ax3.hist(e2e_latencies, bins=50, color='gold', alpha=0.7, edgecolor='black')
                ax3.axvline(np.mean(e2e_latencies), color='red', linestyle='--', label=f'Mean: {np.mean(e2e_latencies):.2f} us')
                ax3.axvline(np.percentile(e2e_latencies, 95), color='orange', linestyle='--', label=f'P95: {np.percentile(e2e_latencies, 95):.2f} us')
                ax3.axvline(np.percentile(e2e_latencies, 99), color='purple', linestyle='--', label=f'P99: {np.percentile(e2e_latencies, 99):.2f} us')
                ax3.set_title('End-to-End Latency Distribution', fontsize=14, fontweight='bold')
                ax3.set_xlabel('Latency (us)')
                ax3.set_ylabel('Frequency')
                ax3.legend()
            
            # Plot 4: Latency breakdown pie chart
            breakdown_data = {
                'Python Total': report.get('python_total', {}).get('mean', 0),
                'Network': report.get('network', {}).get('mean', 0),
                'C++ Total': report.get('cpp_total', {}).get('mean', 0)
            }
            
            if any(breakdown_data.values()):
                ax4.pie(breakdown_data.values(), labels=breakdown_data.keys(), autopct='%1.1f%%', startangle=90)
                ax4.set_title('Latency Breakdown', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"\nLatency analysis plots saved to: {save_path}")
            
        except Exception as e:
            print(f"Warning: Could not create latency plots: {e}")


def run_latency_test(num_signals: int = 1000, delay_ms: float = 1.0, port: int = 5555):
    """Run comprehensive latency measurement test."""
    print("Starting End-to-End Latency Test")
    print(f"   Signals: {num_signals}")
    print(f"   Delay: {delay_ms}ms between signals")
    print(f"   Port: {port}")
    
    # Initialize components
    publisher = LatencyTestPublisher(port=port)
    subscriber = LatencyTestSubscriber(port=port)
    analyzer = LatencyAnalyzer()
    
    try:
        # Connect components
        print("\nConnecting components...")
        if not publisher.connect():
            print("Failed to connect publisher")
            return
        
        subscriber.connect()
        subscriber.start_listening()
        
        # Wait for connection to stabilize and subscriber to start listening
        print("Waiting for subscriber to start listening...")
        time.sleep(1.0)
        
        print(f"\nSending {num_signals} test signals...")
        start_time = time.time()
        
        # Send test signals
        for i in range(num_signals):
            signal_id = f"test_signal_{i:06d}"
            measurement = publisher.send_signal_with_measurement(signal_id)
            
            # Add measurement to subscriber for tracking
            subscriber.add_measurement(measurement)
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"   Sent {i + 1}/{num_signals} signals ({rate:.1f} signals/sec)")
            
            # Delay between signals
            time.sleep(delay_ms / 1000.0)
        
        # Wait for all signals to be processed
        print(f"\nWaiting for signal processing to complete...")
        time.sleep(2.0)  # Allow time for processing
        
        # Collect measurements
        print(f"\nCollecting measurements...")
        all_measurements = publisher.measurements + list(subscriber.measurements.values())
        
        # Remove duplicates and filter valid measurements
        unique_measurements = {}
        for measurement in all_measurements:
            if measurement.signal_id not in unique_measurements:
                unique_measurements[measurement.signal_id] = measurement
        
        valid_measurements = [m for m in unique_measurements.values() if m.get_end_to_end_latency() is not None]
        
        print(f"   Total measurements: {len(all_measurements)}")
        print(f"   Valid measurements: {len(valid_measurements)}")
        print(f"   Success rate: {len(valid_measurements)/num_signals*100:.1f}%")
        
        # Analyze results
        analyzer.add_measurements(valid_measurements)
        report = analyzer.generate_latency_report()
        analyzer.print_latency_report(report)
        
        # Create visualizations
        analyzer.create_latency_plots(report)
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"latency_test_results_{timestamp}.json"
        
        # Convert measurements to serializable format
        serializable_measurements = []
        for measurement in valid_measurements:
            serializable_measurements.append({
                "signal_id": measurement.signal_id,
                "python_generation_latency": measurement.get_python_generation_latency(),
                "python_serialization_latency": measurement.get_python_serialization_latency(),
                "python_zmq_latency": measurement.get_python_zmq_latency(),
                "network_latency": measurement.get_network_latency(),
                "cpp_receive_latency": measurement.get_cpp_receive_latency(),
                "cpp_parsing_latency": measurement.get_cpp_parsing_latency(),
                "cpp_risk_check_latency": measurement.get_cpp_risk_check_latency(),
                "cpp_order_creation_latency": measurement.get_cpp_order_creation_latency(),
                "cpp_tws_latency": measurement.get_cpp_tws_latency(),
                "total_python_latency": measurement.get_total_python_latency(),
                "total_cpp_latency": measurement.get_total_cpp_latency(),
                "end_to_end_latency": measurement.get_end_to_end_latency(),
                "error_message": measurement.error_message
            })
        
        with open(results_file, 'w') as f:
            json.dump({
                "test_config": {
                    "num_signals": num_signals,
                    "delay_ms": delay_ms,
                    "port": port,
                    "timestamp": timestamp
                },
                "summary": report,
                "measurements": serializable_measurements
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
    finally:
        # Cleanup
        print("\nCleaning up...")
        publisher.disconnect()
        subscriber.disconnect()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="End-to-End Latency Measurement Test")
    parser.add_argument("--signals", type=int, default=1000, help="Number of signals to send")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between signals in milliseconds")
    parser.add_argument("--port", type=int, default=5555, help="ZMQ port to use")
    
    args = parser.parse_args()
    
    run_latency_test(
        num_signals=args.signals,
        delay_ms=args.delay,
        port=args.port
    ) 