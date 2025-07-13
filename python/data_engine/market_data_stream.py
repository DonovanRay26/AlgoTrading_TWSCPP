"""
Market data streaming from Interactive Brokers TWS.
Provides real-time price data for pairs trading signal generation.
"""

import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np

from ib_insync import *
from monitoring.logging_config import get_logger


class MarketDataStreamer:
    """
    Real-time market data streamer for IBKR TWS.
    Handles connection, data streaming, and price management for pairs trading.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        """
        Initialize the market data streamer.
        
        Args:
            host: TWS host address (127.0.0.1 for local TWS)
            port: TWS port (7497 for TWS, 4001 for IB Gateway)
            client_id: Unique client ID for this connection
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        
        # IB connection
        self.ib = IB()
        self.is_connected = False
        self.connection_thread = None
        
        # Data storage
        self.price_data: Dict[str, Dict[str, Any]] = {}
        self.latest_prices: Dict[str, float] = {}
        self.data_lock = threading.Lock()
        
        # Subscription tracking
        self.subscribed_symbols: List[str] = []
        self.ticker_ids: Dict[str, int] = {}
        
        # Logging
        self.logger = get_logger("MarketDataStreamer")
        
        # Connection status
        self.connection_attempts = 0
        self.max_connection_attempts = 5
        self.reconnect_delay = 5  # seconds
        
    def connect(self) -> bool:
        """Connect to IBKR TWS."""
        try:
            self.logger.info(f"Connecting to TWS at {self.host}:{self.port}")
            
            # Connect to TWS
            self.ib.connect(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                timeout=20
            )
            
            # Wait for connection
            time.sleep(2)
            
            if self.ib.isConnected():
                self.is_connected = True
                self.connection_attempts = 0
                self.logger.info("Successfully connected to TWS")
                
                # Set up error handling
                self.ib.errorEvent += self._on_error
                self.ib.disconnectedEvent += self._on_disconnect
                
                return True
            else:
                self.logger.error("Failed to connect to TWS")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from TWS."""
        try:
            if self.is_connected:
                # Cancel all market data subscriptions
                for symbol in self.subscribed_symbols:
                    self._cancel_market_data(symbol)
                
                # Disconnect
                self.ib.disconnect()
                self.is_connected = False
                self.logger.info("Disconnected from TWS")
                
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")
    
    def start(self):
        """Start the market data streamer."""
        if not self.is_connected:
            if not self.connect():
                self.logger.error("Failed to start - cannot connect to TWS")
                return False
        
        self.logger.info("Market data streamer started")
        return True
    
    def stop(self):
        """Stop the market data streamer."""
        self.disconnect()
        self.logger.info("Market data streamer stopped")
    
    def subscribe_to_symbols(self, symbols: List[str]) -> bool:
        """
        Subscribe to real-time market data for given symbols.
        
        Args:
            symbols: List of stock symbols to subscribe to
            
        Returns:
            bool: True if subscription successful
        """
        if not self.is_connected:
            self.logger.error("Cannot subscribe - not connected to TWS")
            return False
        
        try:
            for symbol in symbols:
                if symbol not in self.subscribed_symbols:
                    success = self._subscribe_to_symbol(symbol)
                    if success:
                        self.subscribed_symbols.append(symbol)
                        self.logger.info(f"Subscribed to {symbol}")
                    else:
                        self.logger.error(f"Failed to subscribe to {symbol}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error subscribing to symbols: {e}")
            return False
    
    def _subscribe_to_symbol(self, symbol: str) -> bool:
        """Subscribe to a single symbol."""
        try:
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Request market data
            ticker = self.ib.reqMktData(contract)
            
            # Store ticker ID for later reference
            self.ticker_ids[symbol] = ticker.contract.conId
            
            # Initialize price data storage
            with self.data_lock:
                self.price_data[symbol] = {
                    'bid': 0.0,
                    'ask': 0.0,
                    'last': 0.0,
                    'close': 0.0,
                    'volume': 0,
                    'timestamp': None
                }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error subscribing to {symbol}: {e}")
            return False
    
    def _cancel_market_data(self, symbol: str):
        """Cancel market data subscription for a symbol."""
        try:
            if symbol in self.ticker_ids:
                contract = Stock(symbol, 'SMART', 'USD')
                self.ib.cancelMktData(contract)
                del self.ticker_ids[symbol]
                self.logger.info(f"Cancelled market data for {symbol}")
        except Exception as e:
            self.logger.error(f"Error cancelling market data for {symbol}: {e}")
    
    def get_latest_data(self) -> Dict[str, float]:
        """
        Get latest price data for all subscribed symbols.
        
        Returns:
            Dict mapping symbol to latest price (mid-price or last price)
        """
        with self.data_lock:
            latest_data = {}
            
            for symbol in self.subscribed_symbols:
                if symbol in self.price_data:
                    data = self.price_data[symbol]
                    
                    # Use mid-price if available, otherwise last price
                    if data['bid'] > 0 and data['ask'] > 0:
                        price = (data['bid'] + data['ask']) / 2
                    elif data['last'] > 0:
                        price = data['last']
                    elif data['close'] > 0:
                        price = data['close']
                    else:
                        price = 0.0
                    
                    if price > 0:
                        latest_data[symbol] = price
                        self.latest_prices[symbol] = price
            
            return latest_data
    
    def get_symbol_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get detailed data for a specific symbol."""
        with self.data_lock:
            return self.price_data.get(symbol, None)
    
    def is_symbol_active(self, symbol: str) -> bool:
        """Check if a symbol has recent price data."""
        with self.data_lock:
            if symbol in self.price_data:
                data = self.price_data[symbol]
                # Check if we have recent data (within last 5 minutes)
                if data['timestamp']:
                    time_diff = (datetime.now() - data['timestamp']).total_seconds()
                    return time_diff < 300  # 5 minutes
            return False
    
    def _on_tick_price(self, ticker, field, price, attrib):
        """Handle tick price updates from TWS."""
        try:
            symbol = ticker.contract.symbol
            
            with self.data_lock:
                if symbol in self.price_data:
                    data = self.price_data[symbol]
                    
                    if field == TickType.BID:
                        data['bid'] = price
                    elif field == TickType.ASK:
                        data['ask'] = price
                    elif field == TickType.LAST:
                        data['last'] = price
                    elif field == TickType.CLOSE:
                        data['close'] = price
                    
                    data['timestamp'] = datetime.now()
                    
                    # Update latest price
                    if data['bid'] > 0 and data['ask'] > 0:
                        self.latest_prices[symbol] = (data['bid'] + data['ask']) / 2
                    elif data['last'] > 0:
                        self.latest_prices[symbol] = data['last']
                    elif data['close'] > 0:
                        self.latest_prices[symbol] = data['close']
            
        except Exception as e:
            self.logger.error(f"Error processing tick price: {e}")
    
    def _on_tick_size(self, ticker, field, size):
        """Handle tick size updates from TWS."""
        try:
            symbol = ticker.contract.symbol
            
            with self.data_lock:
                if symbol in self.price_data:
                    if field == TickType.VOLUME:
                        self.price_data[symbol]['volume'] = size
                        
        except Exception as e:
            self.logger.error(f"Error processing tick size: {e}")
    
    def _on_error(self, reqId, errorCode, errorString, contract):
        """Handle TWS errors."""
        if errorCode in [2104, 2106, 2158]:  # Market data farm connection messages
            self.logger.info(f"TWS Info: {errorString}")
        else:
            self.logger.error(f"TWS Error {errorCode}: {errorString}")
    
    def _on_disconnect(self):
        """Handle TWS disconnection."""
        self.logger.warning("Disconnected from TWS")
        self.is_connected = False
        
        # Attempt reconnection
        if self.connection_attempts < self.max_connection_attempts:
            self.connection_attempts += 1
            self.logger.info(f"Attempting reconnection {self.connection_attempts}/{self.max_connection_attempts}")
            
            # Start reconnection thread
            reconnect_thread = threading.Thread(target=self._reconnect, daemon=True)
            reconnect_thread.start()
    
    def _reconnect(self):
        """Attempt to reconnect to TWS."""
        time.sleep(self.reconnect_delay)
        
        if self.connect():
            # Resubscribe to symbols
            symbols_to_resubscribe = self.subscribed_symbols.copy()
            self.subscribed_symbols.clear()
            self.subscribe_to_symbols(symbols_to_resubscribe)
            self.logger.info("Successfully reconnected and resubscribed")
        else:
            self.logger.error("Failed to reconnect")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection and subscription status."""
        return {
            'is_connected': self.is_connected,
            'host': self.host,
            'port': self.port,
            'subscribed_symbols': self.subscribed_symbols,
            'active_symbols': [s for s in self.subscribed_symbols if self.is_symbol_active(s)],
            'connection_attempts': self.connection_attempts
        }
    
    def wait_for_data(self, symbols: List[str], timeout: int = 30) -> bool:
        """
        Wait for market data to become available for specified symbols.
        
        Args:
            symbols: List of symbols to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if all symbols have data within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_active = True
            
            for symbol in symbols:
                if not self.is_symbol_active(symbol):
                    all_active = False
                    break
            
            if all_active:
                self.logger.info(f"Market data available for all symbols: {symbols}")
                return True
            
            time.sleep(1)
        
        self.logger.warning(f"Timeout waiting for market data for symbols: {symbols}")
        return False


# Global market data streamer instance
_market_data_streamer = None


def get_market_data_streamer(host: str = "127.0.0.1", port: int = 7497) -> MarketDataStreamer:
    """Get or create the global market data streamer instance."""
    global _market_data_streamer
    
    if _market_data_streamer is None:
        _market_data_streamer = MarketDataStreamer(host, port)
    
    return _market_data_streamer


def shutdown_market_data_streamer():
    """Shutdown the global market data streamer."""
    global _market_data_streamer
    
    if _market_data_streamer:
        _market_data_streamer.stop()
        _market_data_streamer = None
