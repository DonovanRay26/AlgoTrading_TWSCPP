"""
Kalman Filter implementation for dynamic hedge ratio calculation in pairs trading.
This module provides the core statistical arbitrage logic for the trading system.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, Any
from pykalman import KalmanFilter
import statsmodels.api as sm

# Temporary logger for testing - will be replaced with proper logging
import logging
logging.basicConfig(level=logging.INFO)
get_logger = lambda name: logging.getLogger(name)


class PairsKalmanFilter:
    """
    Kalman Filter for pairs trading with dynamic hedge ratio estimation.
    
    This implementation uses a state-space model where:
    - State: [intercept, beta] (hedge ratio)
    - Observation: log price of asset A
    - Covariate: log price of asset B
    """
    
    def __init__(self, observation_covariance: float = 0.001, 
                 delta: float = 0.0001,
                 initial_state_covariance: float = 1.0):
        """
        Initialize the Kalman Filter for pairs trading.
        
        Args:
            observation_covariance: Variance of observation noise
            delta: Delta parameter for transition covariance calculation
            initial_state_covariance: Initial state covariance
        """
        self.observation_covariance = observation_covariance
        self.delta = delta
        self.transition_covariance = delta / (1 - delta)  # Matches backtester exactly
        self.initial_state_covariance = initial_state_covariance
        
        self.logger = get_logger("KalmanFilter")
        self.kf = None
        self.is_initialized = False
        
        # State tracking
        self.state_means = None
        self.state_covariances = None
        self.spreads = None
        self.z_scores = None
        self.hedge_ratios = None
        
    def initialize(self, price_a: pd.Series, price_b: pd.Series) -> bool:
        """
        Initialize the Kalman Filter with historical price data.
        
        Args:
            price_a: Price series for asset A
            price_b: Price series for asset B
            
        Returns:
            bool: True if initialization successful
        """
        try:
            if len(price_a) != len(price_b):
                raise ValueError("Price series must have the same length")
            
            if len(price_a) < 50:  # Need minimum data for initialization
                raise ValueError("Need at least 50 data points for initialization")
            
            # Convert to log prices
            log_price_a = np.log(price_a.values)
            log_price_b = np.log(price_b.values)
            
            # Create observation matrix (log price B with constant term)
            observation_matrix = np.column_stack([np.ones(len(log_price_b)), log_price_b])
            
            # Reshape for pykalman (time, observation_dim, state_dim)
            observation_matrices = observation_matrix.reshape(len(log_price_b), 1, 2)
            
            # Initialize Kalman Filter (matches backtester exactly)
            self.kf = KalmanFilter(
                n_dim_obs=1,
                n_dim_state=2,
                initial_state_mean=np.zeros(2),
                initial_state_covariance=np.eye(2) * self.initial_state_covariance,
                transition_matrices=np.eye(2),
                observation_matrices=observation_matrices,
                observation_covariance=self.observation_covariance,
                transition_covariance=np.eye(2) * self.transition_covariance
            )
            
            # Run filter on historical data
            self.state_means, self.state_covariances = self.kf.filter(log_price_a)
            
            # Calculate spreads and z-scores
            self._calculate_spreads_and_z_scores(log_price_a, observation_matrices)
            
            # Store hedge ratios
            self.hedge_ratios = pd.Series(self.state_means[:, 1], index=price_a.index)
            
            self.is_initialized = True
            self.logger.info(f"Kalman Filter initialized with {len(price_a)} data points")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Kalman Filter: {e}")
            self.is_initialized = False
            return False
    
    def _calculate_spreads_and_z_scores(self, log_price_a: np.ndarray, 
                                      observation_matrices: np.ndarray):
        """Calculate spreads and z-scores from Kalman Filter results."""
        # Calculate expected values
        expected_values = (observation_matrices @ 
                          self.state_means.reshape(-1, 2, 1)).flatten()
        
        # Calculate spreads (forecast errors)
        self.spreads = pd.Series(log_price_a - expected_values)
        
        # Calculate z-scores using forecast error variance
        forecast_variances = (observation_matrices @ 
                             self.state_covariances @ 
                             observation_matrices.transpose((0, 2, 1))).flatten()
        
        self.z_scores = pd.Series(self.spreads / np.sqrt(forecast_variances))
    
    def update(self, price_a: float, price_b: float) -> Tuple[float, float, float]:
        """
        Update the Kalman Filter with new price data.
        
        Args:
            price_a: Current price of asset A
            price_b: Current price of asset B
            
        Returns:
            Tuple[float, float, float]: (hedge_ratio, z_score, spread)
        """
        if not self.is_initialized:
            raise RuntimeError("Kalman Filter not initialized. Call initialize() first.")
        
        try:
            # Convert to log prices
            log_price_a = np.log(price_a)
            log_price_b = np.log(price_b)
            
            # Create observation matrix for single observation
            observation_matrix = np.array([[1.0, log_price_b]])
            
            # Get current state
            current_state_mean = self.state_means[-1, :]  # Ensure 1D array
            current_state_covariance = self.state_covariances[-1, :, :]  # Ensure 2D array
            
            # Prediction step
            predicted_state_mean = current_state_mean
            predicted_state_covariance = current_state_covariance + np.eye(2) * self.transition_covariance
            
            # Update step
            kalman_gain = (predicted_state_covariance @ observation_matrix.T @ 
                          np.linalg.inv(observation_matrix @ predicted_state_covariance @ 
                                       observation_matrix.T + self.observation_covariance))
            
            # Update state
            new_state_mean = predicted_state_mean + kalman_gain.flatten() * (log_price_a - 
                                (observation_matrix @ predicted_state_mean)[0, 0])
            new_state_covariance = (np.eye(2) - kalman_gain @ observation_matrix) @ predicted_state_covariance
            
            # Update stored values
            self.state_means = np.vstack([self.state_means, new_state_mean])
            self.state_covariances = np.vstack([self.state_covariances, new_state_covariance.reshape(1, 2, 2)])
            
            # Calculate new spread and z-score
            expected_value = observation_matrix @ new_state_mean
            spread = log_price_a - expected_value[0, 0]
            
            forecast_variance = (observation_matrix @ new_state_covariance @ 
                               observation_matrix.T + self.observation_covariance)[0, 0]
            z_score = spread / np.sqrt(forecast_variance)
            
            # Update hedge ratio
            hedge_ratio = new_state_mean[1]
            
            self.logger.debug(f"Updated KF - Hedge Ratio: {hedge_ratio:.4f}, Z-Score: {z_score:.3f}")
            
            return hedge_ratio, z_score, spread
            
        except Exception as e:
            self.logger.error(f"Error updating Kalman Filter: {e}")
            # Return last known values
            return self.hedge_ratios.iloc[-1], self.z_scores.iloc[-1], self.spreads.iloc[-1]
    
    def get_current_state(self) -> Dict[str, float]:
        """Get current state of the Kalman Filter."""
        if not self.is_initialized:
            return {}
        
        return {
            'hedge_ratio': self.hedge_ratios.iloc[-1],
            'z_score': self.z_scores.iloc[-1],
            'spread': self.spreads.iloc[-1],
            'intercept': self.state_means[-1, 0],
            'state_variance': np.trace(self.state_covariances[-1, :, :])
        }
    
    def get_historical_data(self) -> Dict[str, pd.Series]:
        """Get historical Kalman Filter results."""
        if not self.is_initialized:
            return {}
        
        return {
            'hedge_ratios': self.hedge_ratios,
            'z_scores': self.z_scores,
            'spreads': self.spreads,
            'intercepts': pd.Series(self.state_means[:, 0], index=self.hedge_ratios.index)
        }
    
    def reset(self):
        """Reset the Kalman Filter to uninitialized state."""
        self.kf = None
        self.is_initialized = False
        self.state_means = None
        self.state_covariances = None
        self.spreads = None
        self.z_scores = None
        self.hedge_ratios = None
        self.logger.info("Kalman Filter reset")
    
    def get_confidence(self) -> float:
        """
        Calculate confidence in current hedge ratio estimate.
        Based on state covariance and recent stability.
        """
        if not self.is_initialized:
            return 0.0
        
        try:
            # State variance (lower is better)
            state_variance = np.trace(self.state_covariances[-1])
            
            # Hedge ratio stability (lower variance in recent values is better)
            recent_hedge_ratios = self.hedge_ratios.tail(20)
            hedge_ratio_variance = recent_hedge_ratios.var()
            
            # Normalize variances (empirical thresholds)
            state_confidence = max(0, 1 - state_variance / 0.1)  # Normalize to [0,1]
            stability_confidence = max(0, 1 - hedge_ratio_variance / 0.01)  # Normalize to [0,1]
            
            # Combined confidence
            confidence = (state_confidence + stability_confidence) / 2
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            self.logger.error(f"Error calculating confidence: {e}")
            return 0.5  # Default to medium confidence


class PairsTradingStrategy:
    """
    Complete pairs trading strategy using Kalman Filter.
    Combines Kalman Filter with signal generation and risk management.
    """
    
    def __init__(self, entry_threshold: float = 2.0, exit_threshold: float = 0.5,
                 max_half_life_days: int = 45):
        """
        Initialize the pairs trading strategy.
        
        Args:
            entry_threshold: Z-score threshold for entering positions
            exit_threshold: Z-score threshold for exiting positions
            max_half_life_days: Maximum half-life in days (no trading if exceeded)
        """
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.max_half_life_days = max_half_life_days
        
        self.kalman_filter = PairsKalmanFilter()
        self.logger = get_logger("PairsStrategy")
        
        # Position tracking
        self.current_position = 0  # -1: short spread, 0: flat, 1: long spread
        self.current_half_life = None
        
    def initialize(self, price_a: pd.Series, price_b: pd.Series) -> bool:
        """Initialize the strategy with historical data."""
        success = self.kalman_filter.initialize(price_a, price_b)
        if success:
            # Calculate initial half-life
            self.current_half_life = self._calculate_half_life()
            self.logger.info(f"Strategy initialized with half-life: {self.current_half_life:.2f} days")
        return success
    
    def _calculate_half_life(self) -> float:
        """
        Calculate half-life of the spread using linear regression.
        Half-life is the time it takes for the spread to revert halfway to its mean.
        """
        try:
            spreads = self.kalman_filter.spreads.dropna()
            if len(spreads) < 50:  # Need minimum data
                return float('inf')
            
            # Create lagged spread and spread difference
            lagged_spread = spreads.shift(1).dropna()
            delta_spread = spreads.diff().dropna()
            
            # Align data
            common_idx = lagged_spread.index.intersection(delta_spread.index)
            if len(common_idx) < 30:
                return float('inf')
            
            lagged_spread = lagged_spread.loc[common_idx]
            delta_spread = delta_spread.loc[common_idx]
            
            # Linear regression: delta_spread = alpha + beta * lagged_spread
            X = sm.add_constant(lagged_spread)
            model = sm.OLS(delta_spread, X).fit()
            
            # Half-life = -ln(2) / beta
            beta = model.params[1]
            if beta >= 0:  # Non-stationary
                return float('inf')
            
            half_life = -np.log(2) / beta
            
            return half_life
            
        except Exception as e:
            self.logger.error(f"Error calculating half-life: {e}")
            return float('inf')
    
    def update(self, price_a: float, price_b: float) -> Dict[str, Any]:
        """
        Update strategy with new price data and generate signals.
        
        Args:
            price_a: Current price of asset A
            price_b: Current price of asset B
            
        Returns:
            Dict containing signal information
        """
        try:
            # Update Kalman Filter
            hedge_ratio, z_score, spread = self.kalman_filter.update(price_a, price_b)
            confidence = self.kalman_filter.get_confidence()
            
            # Update half-life periodically (every 20 updates to avoid excessive calculation)
            if hasattr(self, '_update_count'):
                self._update_count += 1
            else:
                self._update_count = 1
            
            if self._update_count % 20 == 0:
                self.current_half_life = self._calculate_half_life()
                self.logger.debug(f"Updated half-life: {self.current_half_life:.2f} days")
            
            # Generate trading signal
            signal = self._generate_signal(z_score, confidence)
            
            # Update position tracking
            self._update_position_tracking(signal, z_score)
            
            return {
                'signal': signal,
                'hedge_ratio': hedge_ratio,
                'z_score': z_score,
                'spread': spread,
                'confidence': confidence,
                'current_position': self.current_position,
                'half_life': self.current_half_life
            }
            
        except Exception as e:
            self.logger.error(f"Error updating strategy: {e}")
            return {
                'signal': 'NO_SIGNAL',
                'hedge_ratio': 0.0,
                'z_score': 0.0,
                'spread': 0.0,
                'confidence': 0.0,
                'current_position': self.current_position,
                'half_life': self.current_half_life
            }
    
    def _generate_signal(self, z_score: float, confidence: float) -> str:
        """Generate trading signal based on z-score, confidence, and half-life."""
        # Check half-life condition first (matches backtest)
        if self.current_half_life is not None and self.current_half_life > self.max_half_life_days:
            self.logger.debug(f"No signal: Half-life {self.current_half_life:.2f} > {self.max_half_life_days} days")
            return 'NO_SIGNAL'
        
        # Require minimum confidence for trading
        if confidence < 0.7:
            return 'NO_SIGNAL'
        
        # Entry signals
        if self.current_position == 0:  # No position
            if z_score <= -self.entry_threshold:
                return 'ENTER_LONG_SPREAD'
            elif z_score >= self.entry_threshold:
                return 'ENTER_SHORT_SPREAD'
        
        # Exit signals
        elif self.current_position == 1:  # Long spread position
            if z_score >= -self.exit_threshold:
                return 'EXIT_POSITION'
        elif self.current_position == -1:  # Short spread position
            if z_score <= self.exit_threshold:
                return 'EXIT_POSITION'
        
        return 'NO_SIGNAL'
    
    def _update_position_tracking(self, signal: str, z_score: float):
        """Update position tracking based on signal."""
        if signal == 'ENTER_LONG_SPREAD':
            self.current_position = 1
        elif signal == 'ENTER_SHORT_SPREAD':
            self.current_position = -1
        elif signal == 'EXIT_POSITION':
            self.current_position = 0
    
    def get_strategy_state(self) -> Dict[str, Any]:
        return {
            "current_position": getattr(self, "current_position", 0),
            "position_entry_date": getattr(self, "position_entry_date", None),
            "position_entry_z_score": getattr(self, "position_entry_z_score", None),
            "half_life": getattr(self, "half_life", float('inf')),
            "kalman_state": self.kalman_filter.get_current_state() if self.kalman_filter else {},
        }
