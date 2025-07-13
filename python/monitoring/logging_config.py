"""
Logging configuration for the pairs trading system.
Provides centralized logging setup with file and console output.
"""

import logging
import colorlog
import os
from datetime import datetime
from pathlib import Path


class TradingLogger:
    """Centralized logging system for the trading application."""
    
    def __init__(self, log_level="INFO", log_file="logs/trading.log"):
        self.log_level = getattr(logging, log_level.upper())
        self.log_file = log_file
        self.logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration with both file and console handlers."""
        # Create logs directory if it doesn't exist
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('TradingSystem')
        self.logger.setLevel(self.log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        
        # Color formatter for console
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(self.log_level)
        
        # File formatter (no colors)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def get_logger(self, name=None):
        """Get a logger instance with the specified name."""
        if name:
            return logging.getLogger(f'TradingSystem.{name}')
        return self.logger
    
    def log_trade_signal(self, pair_name, signal_type, z_score, confidence):
        """Log trading signals with specific formatting."""
        self.logger.info(
            f"TRADE SIGNAL: {pair_name} | {signal_type} | Z-Score: {z_score:.3f} | "
            f"Confidence: {confidence:.3f}"
        )
    
    def log_position_update(self, pair_name, position_type, shares_a, shares_b, value):
        """Log position updates."""
        self.logger.info(
            f"POSITION UPDATE: {pair_name} | {position_type} | "
            f"Shares A: {shares_a} | Shares B: {shares_b} | Value: ${value:,.2f}"
        )
    
    def log_performance(self, pnl, total_return, sharpe_ratio):
        """Log performance metrics."""
        self.logger.info(
            f"PERFORMANCE: P&L: ${pnl:,.2f} | Total Return: {total_return:.2%} | "
            f"Sharpe: {sharpe_ratio:.3f}"
        )
    
    def log_error(self, error_msg, error_type="ERROR"):
        """Log errors with specific formatting."""
        self.logger.error(f"ERROR [{error_type}]: {error_msg}")
    
    def log_warning(self, warning_msg):
        """Log warnings."""
        self.logger.warning(f"WARNING: {warning_msg}")


# Global logger instance
trading_logger = TradingLogger()


def get_logger(name=None):
    """Get a logger instance for the specified module."""
    return trading_logger.get_logger(name)


def log_trade_signal(pair_name, signal_type, z_score, confidence):
    """Log a trading signal."""
    trading_logger.log_trade_signal(pair_name, signal_type, z_score, confidence)


def log_position_update(pair_name, position_type, shares_a, shares_b, value):
    """Log a position update."""
    trading_logger.log_position_update(pair_name, position_type, shares_a, shares_b, value)


def log_performance(pnl, total_return, sharpe_ratio):
    """Log performance metrics."""
    trading_logger.log_performance(pnl, total_return, sharpe_ratio)


def log_error(error_msg, error_type="ERROR"):
    """Log an error."""
    trading_logger.log_error(error_msg, error_type)


def log_warning(warning_msg):
    """Log a warning."""
    trading_logger.log_warning(warning_msg)
