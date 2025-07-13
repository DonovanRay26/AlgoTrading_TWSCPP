"""
Signal publisher for ZMQ communication with C++ order execution engine.
Handles sending trading signals and system messages via ZeroMQ.
"""

import zmq
import json
import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime

from .message_protocol import (
    TradeSignal, PositionUpdate, PerformanceUpdate, 
    SystemStatus, ErrorMessage, create_heartbeat,
    SignalType, MessageType
)
# Temporary logger for testing - will be replaced with proper logging
import logging
logging.basicConfig(level=logging.INFO)
get_logger = lambda name: logging.getLogger(name)


class SignalPublisher:
    """ZMQ publisher for sending trading signals and system messages."""
    
    def __init__(self, host: str = "localhost", port: int = 5555):
        self.host = host
        self.port = port
        self.context = zmq.Context()
        self.socket = None
        self.logger = get_logger("SignalPublisher")
        self.is_connected = False
        self.heartbeat_thread = None
        self.stop_heartbeat = False
        
    def connect(self) -> bool:
        """Connect to ZMQ socket."""
        try:
            self.socket = self.context.socket(zmq.PUB)
            self.socket.bind(f"tcp://{self.host}:{self.port}")
            
            # Allow time for socket to bind
            time.sleep(0.1)
            
            self.is_connected = True
            self.logger.info(f"Connected to ZMQ publisher on {self.host}:{self.port}")
            
            # Start heartbeat thread
            self._start_heartbeat()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to ZMQ publisher: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from ZMQ socket."""
        self.stop_heartbeat = True
        
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2.0)
        
        if self.socket:
            self.socket.close()
            self.socket = None
        
        self.is_connected = False
        self.logger.info("Disconnected from ZMQ publisher")
    
    def _start_heartbeat(self):
        """Start heartbeat thread to maintain connection."""
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat messages."""
        while not self.stop_heartbeat:
            try:
                if self.is_connected:
                    heartbeat = create_heartbeat("PythonDataEngine")
                    # Convert heartbeat to dict before sending
                    if hasattr(heartbeat, 'to_dict'):
                        heartbeat_dict = heartbeat.to_dict()
                    else:
                        heartbeat_dict = json.loads(heartbeat.to_json())
                    self._send_message("HEARTBEAT", heartbeat_dict)
                time.sleep(30)  # Send heartbeat every 30 seconds
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                time.sleep(5)
    
    def _send_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """Send a message with the specified topic."""
        if not self.is_connected or not self.socket:
            self.logger.error("Not connected to ZMQ socket")
            return False
        
        try:
            # Send topic and message
            self.socket.send_string(topic, zmq.SNDMORE)
            self.socket.send_json(message)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    def send_trade_signal(self, trade_signal: TradeSignal) -> bool:
        """Send a trade signal."""
        if not self.is_connected:
            self.logger.error("Cannot send trade signal: not connected")
            return False
        
        try:
            # Convert to dict and send
            if hasattr(trade_signal, 'to_dict'):
                message_dict = trade_signal.to_dict()
            else:
                message_dict = json.loads(trade_signal.to_json())
            success = self._send_message("TRADE_SIGNAL", message_dict)
            
            if success:
                self.logger.info(
                    f"Sent trade signal: {trade_signal.pair_name} | "
                    f"{trade_signal.signal_type} | Z-Score: {trade_signal.z_score:.3f}"
                )
            else:
                self.logger.error("Failed to send trade signal")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending trade signal: {e}")
            return False
    
    def send_position_update(self, position_update: PositionUpdate) -> bool:
        """Send a position update."""
        if not self.is_connected:
            return False
        
        try:
            if hasattr(position_update, 'to_dict'):
                message_dict = position_update.to_dict()
            else:
                message_dict = json.loads(position_update.to_json())
            success = self._send_message("POSITION_UPDATE", message_dict)
            
            if success:
                self.logger.debug(
                    f"Sent position update: {position_update.pair_name} | "
                    f"Position: {position_update.current_position}"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending position update: {e}")
            return False
    
    def send_performance_update(self, performance_update: PerformanceUpdate) -> bool:
        """Send a performance update."""
        if not self.is_connected:
            return False
        
        try:
            if hasattr(performance_update, 'to_dict'):
                message_dict = performance_update.to_dict()
            else:
                message_dict = json.loads(performance_update.to_json())
            success = self._send_message("PERFORMANCE_UPDATE", message_dict)
            
            if success:
                self.logger.info(
                    f"Sent performance update: P&L: ${performance_update.total_pnl:,.2f} | "
                    f"Return: {performance_update.total_return:.2%}"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending performance update: {e}")
            return False
    
    def send_system_status(self, status: str, component: str, message: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send a system status message."""
        if not self.is_connected:
            return False
        
        try:
            system_status = SystemStatus(
                message_id="",
                timestamp="",
                status=status,
                component=component,
                uptime_seconds=0.0,  # TODO: Calculate actual uptime
                memory_usage_mb=0.0,  # TODO: Get actual memory usage
                cpu_usage_percent=0.0,  # TODO: Get actual CPU usage
                message=message,
                metadata=metadata or {}
            )
            
            if hasattr(system_status, 'to_dict'):
                message_dict = system_status.to_dict()
            else:
                message_dict = json.loads(system_status.to_json())
            success = self._send_message("SYSTEM_STATUS", message_dict)
            
            if success:
                self.logger.info(f"Sent system status: {component} - {status}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending system status: {e}")
            return False
    
    def send_error_message(self, error_type: str, error_code: str, error_message: str,
                          severity: str, component: str, pair_name: Optional[str] = None) -> bool:
        """Send an error message."""
        if not self.is_connected:
            return False
        
        try:
            error_msg = ErrorMessage(
                message_id="",
                timestamp="",
                error_type=error_type,
                error_code=error_code,
                error_message=error_message,
                severity=severity,
                component=component,
                pair_name=pair_name
            )
            
            message_dict = json.loads(error_msg.to_json())
            success = self._send_message("ERROR_MESSAGE", message_dict)
            
            if success:
                self.logger.error(f"Sent error message: {error_type} - {error_message}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending error message: {e}")
            return False
    
    def send_quick_signal(self, pair_name: str, symbol_a: str, symbol_b: str,
                         signal_type: SignalType, z_score: float, hedge_ratio: float,
                         confidence: float, position_size: int, shares_a: int, shares_b: int,
                         volatility: float, correlation: float) -> bool:
        """Send a quick trade signal with minimal parameters."""
        try:
            trade_signal = TradeSignal(
                message_id="",
                timestamp="",
                pair_name=pair_name,
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                signal_type=signal_type.value,
                z_score=z_score,
                hedge_ratio=hedge_ratio,
                confidence=confidence,
                position_size=position_size,
                shares_a=shares_a,
                shares_b=shares_b,
                volatility=volatility,
                correlation=correlation
            )
            
            return self.send_trade_signal(trade_signal)
            
        except Exception as e:
            self.logger.error(f"Error creating quick signal: {e}")
            return False
    
    def is_healthy(self) -> bool:
        """Check if the publisher is healthy and connected."""
        return self.is_connected and self.socket is not None


# Global publisher instance
_signal_publisher = None


def get_signal_publisher(host: str = "localhost", port: int = 5555) -> SignalPublisher:
    """Get or create the global signal publisher instance."""
    global _signal_publisher
    
    if _signal_publisher is None:
        _signal_publisher = SignalPublisher(host, port)
        _signal_publisher.connect()
    
    return _signal_publisher


def shutdown_signal_publisher():
    """Shutdown the global signal publisher."""
    global _signal_publisher
    
    if _signal_publisher:
        _signal_publisher.disconnect()
        _signal_publisher = None
