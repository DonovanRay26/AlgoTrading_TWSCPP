"""
Message protocol for ZMQ communication between Python data engine and C++ order execution.
Defines the JSON message structure for trading signals and system messages.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class SignalType(Enum):
    """Enumeration of possible trading signal types."""
    ENTER_LONG_SPREAD = "ENTER_LONG_SPREAD"    # Long A, Short B
    ENTER_SHORT_SPREAD = "ENTER_SHORT_SPREAD"  # Short A, Long B
    EXIT_POSITION = "EXIT_POSITION"            # Close all positions
    NO_SIGNAL = "NO_SIGNAL"                    # No action needed


class MessageType(Enum):
    """Enumeration of message types for system communication."""
    TRADE_SIGNAL = "TRADE_SIGNAL"
    POSITION_UPDATE = "POSITION_UPDATE"
    PERFORMANCE_UPDATE = "PERFORMANCE_UPDATE"
    SYSTEM_STATUS = "SYSTEM_STATUS"
    ERROR_MESSAGE = "ERROR_MESSAGE"
    HEARTBEAT = "HEARTBEAT"


@dataclass
class TradeSignal:
    """Data structure for trading signals."""
    # Required fields (no defaults)
    pair_name: str
    symbol_a: str
    symbol_b: str
    signal_type: str
    z_score: float
    hedge_ratio: float
    confidence: float
    position_size: int
    shares_a: int
    shares_b: int
    volatility: float
    correlation: float
    
    # Optional fields (with defaults)
    message_id: str = ""
    timestamp: str = ""
    message_type: str = MessageType.TRADE_SIGNAL.value
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Generate message ID and timestamp if not provided."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TradeSignal':
        """Create TradeSignal from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class PositionUpdate:
    """Data structure for position updates."""
    # Required fields (no defaults)
    pair_name: str
    symbol_a: str
    symbol_b: str
    current_position: str  # "LONG_SPREAD", "SHORT_SPREAD", "FLAT"
    shares_a: int
    shares_b: int
    market_value: float
    unrealized_pnl: float
    price_a: float
    price_b: float
    
    # Optional fields (with defaults)
    message_id: str = ""
    timestamp: str = ""
    message_type: str = MessageType.POSITION_UPDATE.value
    
    def __post_init__(self):
        """Generate message ID and timestamp if not provided."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PositionUpdate':
        """Create PositionUpdate from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class PerformanceUpdate:
    """Data structure for performance updates."""
    # Required fields (no defaults)
    total_pnl: float
    daily_pnl: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_positions: int
    active_pairs: int
    cash_balance: float
    
    # Optional fields (with defaults)
    message_id: str = ""
    timestamp: str = ""
    message_type: str = MessageType.PERFORMANCE_UPDATE.value
    
    def __post_init__(self):
        """Generate message ID and timestamp if not provided."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PerformanceUpdate':
        """Create PerformanceUpdate from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class SystemStatus:
    """Data structure for system status messages."""
    # Required fields (no defaults)
    status: str  # "RUNNING", "STOPPED", "ERROR", "MAINTENANCE"
    component: str  # "DATA_ENGINE", "ORDER_EXECUTION", "RISK_MANAGER"
    uptime_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    message: str
    
    # Optional fields (with defaults)
    message_id: str = ""
    timestamp: str = ""
    message_type: str = MessageType.SYSTEM_STATUS.value
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Generate message ID and timestamp if not provided."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SystemStatus':
        """Create SystemStatus from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class ErrorMessage:
    """Data structure for error messages."""
    # Required fields (no defaults)
    error_type: str  # "DATA_ERROR", "ORDER_ERROR", "SYSTEM_ERROR"
    error_code: str
    error_message: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    component: str
    
    # Optional fields (with defaults)
    message_id: str = ""
    timestamp: str = ""
    message_type: str = MessageType.ERROR_MESSAGE.value
    pair_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Generate message ID and timestamp if not provided."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ErrorMessage':
        """Create ErrorMessage from JSON string."""
        data = json.loads(json_str)
        return cls(**data)


def create_trade_signal(
    pair_name: str,
    symbol_a: str,
    symbol_b: str,
    signal_type: SignalType,
    z_score: float,
    hedge_ratio: float,
    confidence: float,
    position_size: int,
    shares_a: int,
    shares_b: int,
    volatility: float,
    correlation: float,
    metadata: Optional[Dict[str, Any]] = None
) -> TradeSignal:
    """Create a trade signal message."""
    return TradeSignal(
        message_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
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
        correlation=correlation,
        metadata=metadata or {}
    )


def parse_message(json_str: str) -> Any:
    """Parse a JSON message and return the appropriate message object."""
    try:
        data = json.loads(json_str)
        message_type = data.get('message_type')
        
        if message_type == MessageType.TRADE_SIGNAL.value:
            return TradeSignal.from_json(json_str)
        elif message_type == MessageType.POSITION_UPDATE.value:
            return PositionUpdate.from_json(json_str)
        elif message_type == MessageType.PERFORMANCE_UPDATE.value:
            return PerformanceUpdate.from_json(json_str)
        elif message_type == MessageType.SYSTEM_STATUS.value:
            return SystemStatus.from_json(json_str)
        elif message_type == MessageType.ERROR_MESSAGE.value:
            return ErrorMessage.from_json(json_str)
        else:
            raise ValueError(f"Unknown message type: {message_type}")
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    except Exception as e:
        raise ValueError(f"Error parsing message: {e}")


@dataclass
class Heartbeat:
    """Data structure for heartbeat messages."""
    component: str
    
    # Optional fields (with defaults)
    message_id: str = ""
    timestamp: str = ""
    message_type: str = MessageType.HEARTBEAT.value
    
    def __post_init__(self):
        """Generate message ID and timestamp if not provided."""
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self), indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


def create_heartbeat(component: str) -> Heartbeat:
    """Create a heartbeat message."""
    return Heartbeat(component=component)
