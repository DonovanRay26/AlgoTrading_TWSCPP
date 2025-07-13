"""
Data processor for cleaning and validating market data from TWS.
Ensures data quality for pairs trading signal generation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

from monitoring.logging_config import get_logger


class DataProcessor:
    """
    Data processor for market data validation and cleaning.
    Ensures high-quality data for pairs trading signal generation.
    """
    
    def __init__(self):
        """Initialize the data processor."""
        self.logger = get_logger("DataProcessor")
        
        # Data quality thresholds
        self.min_price = 0.01  # Minimum valid price
        self.max_price = 10000.0  # Maximum valid price
        self.max_price_change = 0.5  # Maximum 50% price change in one update
        self.min_volume = 0  # Minimum volume (0 for now)
        
        # Data validation history
        self.validation_history: Dict[str, List[Dict]] = {}
        
    def validate_price_data(self, symbol: str, price: float, 
                          previous_price: Optional[float] = None) -> Tuple[bool, str]:
        """
        Validate a single price data point.
        
        Args:
            symbol: Stock symbol
            price: Current price
            previous_price: Previous price for change validation
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Basic price range validation
        if price <= self.min_price:
            return False, f"Price too low: {price}"
        
        if price > self.max_price:
            return False, f"Price too high: {price}"
        
        # Price change validation
        if previous_price and previous_price > 0:
            price_change = abs(price - previous_price) / previous_price
            
            if price_change > self.max_price_change:
                return False, f"Price change too large: {price_change:.2%}"
        
        return True, "Valid"
    
    def clean_price_data(self, price_data: Dict[str, float]) -> Dict[str, float]:
        """
        Clean and validate price data dictionary.
        
        Args:
            price_data: Dictionary of symbol -> price
            
        Returns:
            Cleaned price data dictionary
        """
        cleaned_data = {}
        
        for symbol, price in price_data.items():
            is_valid, reason = self.validate_price_data(symbol, price)
            
            if is_valid:
                cleaned_data[symbol] = price
            else:
                self.logger.warning(f"Invalid price for {symbol}: {reason}")
                
                # Store validation failure
                if symbol not in self.validation_history:
                    self.validation_history[symbol] = []
                
                self.validation_history[symbol].append({
                    'timestamp': datetime.now(),
                    'price': price,
                    'reason': reason
                })
        
        return cleaned_data
    
    def align_pair_data(self, symbol_a: str, symbol_b: str, 
                       price_data: Dict[str, float]) -> Optional[Tuple[float, float]]:
        """
        Align price data for a trading pair.
        
        Args:
            symbol_a: First symbol in pair
            symbol_b: Second symbol in pair
            price_data: Dictionary of all price data
            
        Returns:
            Tuple of (price_a, price_b) if both valid, None otherwise
        """
        if symbol_a not in price_data or symbol_b not in price_data:
            return None
        
        price_a = price_data[symbol_a]
        price_b = price_data[symbol_b]
        
        # Validate both prices
        is_valid_a, reason_a = self.validate_price_data(symbol_a, price_a)
        is_valid_b, reason_b = self.validate_price_data(symbol_b, price_b)
        
        if not is_valid_a:
            self.logger.warning(f"Invalid price for {symbol_a}: {reason_a}")
            return None
        
        if not is_valid_b:
            self.logger.warning(f"Invalid price for {symbol_b}: {reason_b}")
            return None
        
        return price_a, price_b
    
    def detect_data_quality_issues(self, symbol: str, 
                                 recent_prices: List[float]) -> List[str]:
        """
        Detect data quality issues in recent price data.
        
        Args:
            symbol: Stock symbol
            recent_prices: List of recent prices
            
        Returns:
            List of detected issues
        """
        issues = []
        
        if not recent_prices:
            issues.append("No price data available")
            return issues
        
        # Check for zero or negative prices
        if any(p <= 0 for p in recent_prices):
            issues.append("Zero or negative prices detected")
        
        # Check for extreme price changes
        if len(recent_prices) > 1:
            price_changes = []
            for i in range(1, len(recent_prices)):
                if recent_prices[i-1] > 0:
                    change = abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                    price_changes.append(change)
            
            if price_changes and max(price_changes) > self.max_price_change:
                issues.append(f"Extreme price changes detected: {max(price_changes):.2%}")
        
        # Check for stale data (if timestamps available)
        # This would be implemented if we track timestamps
        
        return issues
    
    def calculate_basic_statistics(self, symbol: str, 
                                 price_data: pd.Series) -> Dict[str, float]:
        """
        Calculate basic statistics for price data.
        
        Args:
            symbol: Stock symbol
            price_data: Series of price data
            
        Returns:
            Dictionary of statistics
        """
        if price_data.empty:
            return {}
        
        stats = {
            'mean': float(price_data.mean()),
            'std': float(price_data.std()),
            'min': float(price_data.min()),
            'max': float(price_data.max()),
            'count': len(price_data)
        }
        
        # Calculate volatility (annualized)
        if len(price_data) > 1:
            returns = price_data.pct_change().dropna()
            if not returns.empty:
                stats['volatility'] = float(returns.std() * np.sqrt(252 * 24 * 60))  # Assuming minute data
        
        return stats
    
    def check_data_freshness(self, symbol: str, 
                           last_update: datetime) -> Tuple[bool, str]:
        """
        Check if data is fresh (recently updated).
        
        Args:
            symbol: Stock symbol
            last_update: Timestamp of last update
            
        Returns:
            Tuple of (is_fresh, reason)
        """
        if not last_update:
            return False, "No timestamp available"
        
        time_diff = datetime.now() - last_update
        
        if time_diff > timedelta(minutes=5):
            return False, f"Data stale: {time_diff.total_seconds() / 60:.1f} minutes old"
        
        if time_diff > timedelta(minutes=1):
            return False, f"Data delayed: {time_diff.total_seconds() / 60:.1f} minutes old"
        
        return True, "Fresh"
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of data validation results."""
        summary = {
            'total_validations': 0,
            'failed_validations': 0,
            'symbols_with_issues': [],
            'recent_issues': []
        }
        
        for symbol, history in self.validation_history.items():
            summary['total_validations'] += len(history)
            failed_count = len([h for h in history if h['reason'] != 'Valid'])
            summary['failed_validations'] += failed_count
            
            if failed_count > 0:
                summary['symbols_with_issues'].append(symbol)
                
                # Get recent issues (last 10)
                recent_issues = sorted(history, key=lambda x: x['timestamp'], reverse=True)[:10]
                summary['recent_issues'].extend(recent_issues)
        
        return summary
    
    def reset_validation_history(self):
        """Reset validation history."""
        self.validation_history.clear()
        self.logger.info("Validation history reset")


# Global data processor instance
_data_processor = None


def get_data_processor() -> DataProcessor:
    """Get or create the global data processor instance."""
    global _data_processor
    
    if _data_processor is None:
        _data_processor = DataProcessor()
    
    return _data_processor
