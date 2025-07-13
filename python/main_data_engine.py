"""
Main data engine for the pairs trading system.
Focused on signal generation only - order execution handled by C++ side.

This module:
- Streams real-time market data
- Calculates Kalman Filter hedge ratios
- Generates trading signals based on z-scores
- Sends signals to C++ order execution engine via ZMQ

All order execution, risk management, and PnL tracking is handled by the C++ side.
"""

import yaml
import time
import threading
import signal
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from ib_insync import *
from ib_insync import Stock
from data_engine.market_data_stream import MarketDataStreamer
from data_engine.data_processor import DataProcessor
from strategy.kalman_filter import PairsTradingStrategy
from strategy.kalman_filter import PairsKalmanFilter
from comms.signaler import get_signal_publisher, shutdown_signal_publisher
from comms.message_protocol import SignalType, create_trade_signal
from monitoring.logging_config import get_logger, log_trade_signal, log_error
from monitoring.performance_tracker import PerformanceTracker


class PairsTradingDataEngine:
    """
    Main data engine for pairs trading system.
    Coordinates all components and manages the trading workflow.
    """
    
    def __init__(self, config_path: str = "config/trading_config.yaml"):
        # Setup logging FIRST
        self.logger = get_logger("DataEngine")
        self.config_path = config_path
        self.config = self._load_config()
        
        # Core components
        self.market_data_streamer = None
        self.data_processor = None
        self.risk_manager = None
        self.performance_tracker = None
        self.signal_publisher = None
        
        # Strategy components (one per pair)
        self.strategies: Dict[str, PairsTradingStrategy] = {}
        self.pairs_config = self._load_pairs_config()
        
        # System state
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        # Data storage
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.signal_history: List[Dict[str, Any]] = []
        
        self.logger.info("Pairs Trading Data Engine initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load trading configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            self.logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_pairs_config(self) -> Dict[str, Any]:
        """Load pairs configuration from YAML file."""
        try:
            with open("config/pairs_config.yaml", 'r') as file:
                pairs_config = yaml.safe_load(file)
            self.logger.info("Loaded pairs configuration")
            return pairs_config
        except Exception as e:
            self.logger.error(f"Failed to load pairs configuration: {e}")
            raise
    
    def initialize(self) -> bool:
        """Initialize all components of the data engine."""
        try:
            self.logger.info("Initializing data engine components...")
            
            # Initialize market data streamer
            self.market_data_streamer = MarketDataStreamer(
                host="127.0.0.1",  # TWS host
                port=7497          # TWS port
            )
            
            # Initialize data processor
            self.data_processor = DataProcessor()
            
            # Note: Risk management for order execution is handled by C++ side
            # Python side focuses on signal generation only
            
            # Initialize performance tracker
            self.performance_tracker = PerformanceTracker()
            
            # Initialize signal publisher
            self.signal_publisher = get_signal_publisher(
                host=self.config['communication']['zmq_host'],
                port=self.config['communication']['zmq_port']
            )
            
            # Initialize strategies for each pair
            self._initialize_strategies()
            
            # Note: Historical data loading moved to start() method after IB connection is established
            
            self.logger.info("Data engine initialization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize data engine: {e}")
            return False
    
    def _initialize_strategies(self):
        """Initialize trading strategies for each pair."""
        for pair_config in self.pairs_config['pairs']:
            if not pair_config['enabled']:
                continue
                
            pair_name = pair_config['name']
            symbol_a = pair_config['symbol_a']
            symbol_b = pair_config['symbol_b']
            
            # Create strategy instance with backtester parameters
            strategy = PairsTradingStrategy(
                entry_threshold=self.config['strategy']['entry_threshold'],
                exit_threshold=self.config['strategy']['exit_threshold'],
                max_half_life_days=self.config['strategy']['max_half_life_days']
            )
            
            # Initialize Kalman Filter with backtester parameters
            kalman_config = self.config['strategy']['kalman']
            strategy.kalman_filter = PairsKalmanFilter(
                observation_covariance=kalman_config['observation_covariance'],
                delta=kalman_config['delta'],
                initial_state_covariance=kalman_config['initial_state_covariance']
            )
            
            self.strategies[pair_name] = strategy
            
            # Initialize price data storage
            self.price_data[pair_name] = pd.DataFrame(columns=[symbol_a, symbol_b])
            
            self.logger.info(f"Initialized strategy for pair: {pair_name} ({symbol_a}/{symbol_b})")
    
    def _load_historical_data(self):
        """Load historical data for strategy initialization using IBKR."""
        try:
            # Use the existing IB connection from market data streamer
            ib = self.market_data_streamer.ib
            
            for pair_config in self.pairs_config['pairs']:
                if not pair_config['enabled']:
                    continue
                
                pair_name = pair_config['name']
                symbol_a = pair_config['symbol_a']
                symbol_b = pair_config['symbol_b']
                
                self.logger.info(f"Loading historical data for {pair_name} from IBKR...")
                
                # Create contracts for both symbols
                contract_a = Stock(symbol_a, 'SMART', 'USD')
                contract_b = Stock(symbol_b, 'SMART', 'USD')
                
                # Get historical data (last 252 trading days)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                
                # Request historical data from IBKR
                bars_a = ib.reqHistoricalData(
                    contract_a,
                    end_date.strftime('%Y%m%d %H:%M:%S'),
                    '1 D',  # 1 day bars
                    '1 day',
                    'TRADES',
                    useRTH=True,
                    formatDate=1
                )
                
                bars_b = ib.reqHistoricalData(
                    contract_b,
                    end_date.strftime('%Y%m%d %H:%M:%S'),
                    '1 D',  # 1 day bars
                    '1 day',
                    'TRADES',
                    useRTH=True,
                    formatDate=1
                )
                
                if not bars_a or not bars_b:
                    self.logger.error(f"No historical data received for {pair_name}")
                    continue
                
                # Convert to pandas Series
                price_a = pd.Series([bar.close for bar in bars_a], 
                                   index=pd.to_datetime([bar.date for bar in bars_a]))
                price_b = pd.Series([bar.close for bar in bars_b], 
                                   index=pd.to_datetime([bar.date for bar in bars_b]))
                
                # Align data by common dates
                common_dates = price_a.index.intersection(price_b.index)
                if len(common_dates) < 50:
                    self.logger.error(f"Insufficient common data for {pair_name}: {len(common_dates)} points")
                    continue
                
                price_a = price_a.loc[common_dates]
                price_b = price_b.loc[common_dates]
                
                # Store data
                self.price_data[pair_name] = pd.DataFrame({
                    symbol_a: price_a,
                    symbol_b: price_b
                })
                
                # Initialize strategy with historical data
                strategy = self.strategies[pair_name]
                if strategy.initialize(price_a, price_b):
                    self.logger.info(f"Strategy initialized for {pair_name} with {len(price_a)} data points")
                else:
                    self.logger.error(f"Failed to initialize strategy for {pair_name}")
            
        except Exception as e:
            self.logger.error(f"Error loading historical data from IBKR: {e}")
            raise
    
    def start(self):
        """Start the data engine."""
        if not self.is_running:
            self.is_running = True
            self.shutdown_event.clear()
            
            self.logger.info("Starting pairs trading data engine...")
            
            # Start market data streaming
            if not self.market_data_streamer.start():
                self.logger.error("Failed to start market data streamer")
                return False
            
            # Subscribe to symbols for all pairs
            all_symbols = []
            for pair_config in self.pairs_config['pairs']:
                if pair_config['enabled']:
                    all_symbols.extend([pair_config['symbol_a'], pair_config['symbol_b']])
            
            # Remove duplicates
            all_symbols = list(set(all_symbols))
            
            # Subscribe to market data
            if not self.market_data_streamer.subscribe_to_symbols(all_symbols):
                self.logger.error("Failed to subscribe to market data")
                return False
            
            # Wait for initial data
            if not self.market_data_streamer.wait_for_data(all_symbols, timeout=30):
                self.logger.warning("Timeout waiting for initial market data")
            
            # Load historical data after IB connection is established
            self._load_historical_data()
            
            # Start main processing loop
            self._main_loop()
    
    def stop(self):
        """Stop the data engine."""
        self.logger.info("Stopping data engine...")
        self.is_running = False
        self.shutdown_event.set()
        
        if self.market_data_streamer:
            self.market_data_streamer.stop()
        
        shutdown_signal_publisher()
        self.logger.info("Data engine stopped")
    
    def _main_loop(self):
        """Main processing loop for the data engine."""
        self.logger.info("Entering main processing loop...")
        
        while self.is_running and not self.shutdown_event.is_set():
            try:
                # Process market data updates
                self._process_market_data()
                
                # Generate and send signals
                self._generate_signals()
                
                # Update performance tracking
                self._update_performance()
                
                # Send system status
                self._send_system_status()
                
                # Sleep for update frequency
                time.sleep(self.config['data']['update_frequency'])
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(5)  # Wait before retrying
        
        self.stop()
    
    def _process_market_data(self):
        """Process incoming market data from TWS."""
        try:
            # Get latest market data from TWS
            market_data = self.market_data_streamer.get_latest_data()
            
            if not market_data:
                return
            
            # Clean and validate market data
            cleaned_data = self.data_processor.clean_price_data(market_data)
            
            if not cleaned_data:
                self.logger.warning("No valid market data after cleaning")
                return
            
            # Process each pair
            for pair_name, strategy in self.strategies.items():
                pair_config = next(p for p in self.pairs_config['pairs'] if p['name'] == pair_name)
                symbol_a = pair_config['symbol_a']
                symbol_b = pair_config['symbol_b']
                
                # Align and validate pair data
                pair_prices = self.data_processor.align_pair_data(symbol_a, symbol_b, cleaned_data)
                
                if pair_prices is None:
                    continue
                
                price_a, price_b = pair_prices
                
                # Update price data with validated real-time prices
                current_time = datetime.now()
                self.price_data[pair_name].loc[current_time] = [price_a, price_b]
                
                # Keep only recent data (last 1000 points)
                if len(self.price_data[pair_name]) > 1000:
                    self.price_data[pair_name] = self.price_data[pair_name].tail(1000)
                
                # Log price updates periodically
                if len(self.price_data[pair_name]) % 100 == 0:  # Every 100 updates
                    self.logger.debug(f"Updated prices for {pair_name}: {symbol_a}=${price_a:.2f}, {symbol_b}=${price_b:.2f}")
                
        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")
    
    def _generate_signals(self):
        """Generate trading signals for all pairs."""
        try:
            for pair_name, strategy in self.strategies.items():
                pair_config = next(p for p in self.pairs_config['pairs'] if p['name'] == pair_name)
                symbol_a = pair_config['symbol_a']
                symbol_b = pair_config['symbol_b']
                
                # Get latest prices
                latest_data = self.price_data[pair_name].tail(1)
                if latest_data.empty:
                    continue
                
                price_a = latest_data[symbol_a].iloc[0]
                price_b = latest_data[symbol_b].iloc[0]
                
                # Update strategy
                result = strategy.update(price_a, price_b)
                
                # Check if we have a signal
                if result['signal'] != 'NO_SIGNAL':
                    self._send_trade_signal(pair_name, symbol_a, symbol_b, result)
                
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
    
    def _send_trade_signal(self, pair_name: str, symbol_a: str, symbol_b: str, 
                          result: Dict[str, Any]):
        """Send a trade signal to the C++ order execution engine."""
        try:
            # Determine signal type
            signal_type_map = {
                'ENTER_LONG_SPREAD': SignalType.ENTER_LONG_SPREAD,
                'ENTER_SHORT_SPREAD': SignalType.ENTER_SHORT_SPREAD,
                'EXIT_POSITION': SignalType.EXIT_POSITION
            }
            
            signal_type = signal_type_map.get(result['signal'])
            if not signal_type:
                return
            
            # Calculate position sizes
            position_size = self._calculate_position_size(pair_name, result)
            shares_a, shares_b = self._calculate_shares(symbol_a, symbol_b, 
                                                      result['hedge_ratio'], 
                                                      signal_type, position_size)
            
            # Create trade signal for live execution
            trade_signal = create_trade_signal(
                pair_name=pair_name,
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                signal_type=signal_type,
                z_score=result['z_score'],
                hedge_ratio=result['hedge_ratio'],
                confidence=result['confidence'],
                position_size=position_size,
                shares_a=shares_a,
                shares_b=shares_b,
                volatility=0.0,  # Will be calculated by C++ side if needed
                correlation=0.0   # Will be calculated by C++ side if needed
            )
            
            # Send signal
            if self.signal_publisher.send_trade_signal(trade_signal):
                # Log the signal with half-life information
                half_life_info = f" (Half-life: {result.get('half_life', 'N/A'):.2f} days)" if result.get('half_life') else ""
                log_trade_signal(pair_name, result['signal'], result['z_score'], result['confidence'])
                self.logger.info(f"Signal sent: {result['signal']} for {pair_name} - Z-Score: {result['z_score']:.3f}, Confidence: {result['confidence']:.3f}{half_life_info}")
                
                # Store in history
                self.signal_history.append({
                    'timestamp': datetime.now(),
                    'pair_name': pair_name,
                    'signal': result['signal'],
                    'z_score': result['z_score'],
                    'hedge_ratio': result['hedge_ratio'],
                    'confidence': result['confidence'],
                    'half_life': result.get('half_life')
                })
            
        except Exception as e:
            self.logger.error(f"Error sending trade signal: {e}")
    
    def _calculate_position_size(self, pair_name: str, result: Dict[str, Any]) -> int:
        """Calculate position size for signal generation (live trading)."""
        try:
            # Get allocated capital for this pair
            allocated_capital = self.config['risk']['allocated_capital']
            
            # Get current prices for the pair
            pair_config = next(p for p in self.pairs_config['pairs'] if p['name'] == pair_name)
            symbol_a = pair_config['symbol_a']
            symbol_b = pair_config['symbol_b']
            
            latest_data = self.price_data[pair_name].tail(1)
            if latest_data.empty:
                return 0
                
            price_a = latest_data[symbol_a].iloc[0]
            price_b = latest_data[symbol_b].iloc[0]
            hedge_ratio = result['hedge_ratio']
            
            # Calculate position units (N) using hedge ratio
            N = allocated_capital / (price_a + abs(hedge_ratio) * price_b)
            
            return int(N)
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 100  # Default small position
    
    def _calculate_shares(self, symbol_a: str, symbol_b: str, hedge_ratio: float,
                         signal_type: SignalType, position_size: int) -> tuple:
        """Calculate number of shares for signal generation (live trading)."""
        try:
            # Calculate shares based on signal type
            if signal_type == SignalType.ENTER_LONG_SPREAD:
                # Long spread: long A, short B
                shares_a = position_size
                shares_b = -int(position_size * hedge_ratio)
            elif signal_type == SignalType.ENTER_SHORT_SPREAD:
                # Short spread: short A, long B
                shares_a = -position_size
                shares_b = int(position_size * hedge_ratio)
            else:  # EXIT_POSITION
                shares_a = 0
                shares_b = 0
            
            return shares_a, shares_b
            
        except Exception as e:
            self.logger.error(f"Error calculating shares: {e}")
            return 0, 0
    
    def _update_performance(self):
        """Update performance tracking (minimal for signal generation)."""
        try:
            # Send basic system status - actual P&L tracking handled by C++ side
            if self.performance_tracker:
                self.performance_tracker.update()
                
        except Exception as e:
            self.logger.error(f"Error updating performance: {e}")
    
    def _send_system_status(self):
        """Send system status update."""
        try:
            status = "RUNNING" if self.is_running else "STOPPED"
            self.signal_publisher.send_system_status(
                status=status,
                component="PythonDataEngine",
                message="Data engine operating normally"
            )
        except Exception as e:
            self.logger.error(f"Error sending system status: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            'is_running': self.is_running,
            'active_pairs': len([p for p in self.pairs_config['pairs'] if p['enabled']]),
            'total_signals': len(self.signal_history),
            'strategies': {name: strategy.get_strategy_state() 
                          for name, strategy in self.strategies.items()}
        }


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\nReceived shutdown signal. Stopping data engine...")
    if hasattr(signal_handler, 'data_engine'):
        signal_handler.data_engine.stop()
    sys.exit(0)


def main():
    """Main entry point for the data engine."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and initialize data engine
    data_engine = PairsTradingDataEngine()
    signal_handler.data_engine = data_engine
    
    try:
        # Initialize
        if not data_engine.initialize():
            print("Failed to initialize data engine")
            return
        
        # Start
        data_engine.start()
        
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt")
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        data_engine.stop()


if __name__ == "__main__":
    main()
