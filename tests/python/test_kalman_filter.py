"""
Tests for Kalman Filter implementation in pairs trading strategy.
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add the python directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'python'))

from strategy.kalman_filter import PairsKalmanFilter, PairsTradingStrategy


class TestPairsKalmanFilter(unittest.TestCase):
    """Test cases for PairsKalmanFilter class."""
    
    def setUp(self):
        """Set up test data."""
        # Create synthetic price data for testing
        np.random.seed(42)
        n_points = 100
        
        # Generate correlated price series
        base_price_a = 100.0
        base_price_b = 50.0
        
        # Create trend with some correlation
        trend = np.linspace(0, 10, n_points)
        noise_a = np.random.normal(0, 1, n_points)
        noise_b = np.random.normal(0, 0.5, n_points)
        
        # Correlated price movements
        price_a = base_price_a + trend + noise_a
        price_b = base_price_b + 0.5 * trend + noise_b
        
        # Add some mean reversion to create trading opportunities
        spread = price_a - 2 * price_b
        mean_reversion = -0.1 * (spread - np.mean(spread))
        price_a += mean_reversion
        
        self.price_a = pd.Series(price_a, index=pd.date_range('2024-01-01', periods=n_points, freq='D'))
        self.price_b = pd.Series(price_b, index=pd.date_range('2024-01-01', periods=n_points, freq='D'))
        
        # Initialize Kalman Filter
        self.kf = PairsKalmanFilter(
            observation_covariance=0.001,
            delta=0.0001,
            initial_state_covariance=1.0
        )
    
    def test_initialization(self):
        """Test Kalman Filter initialization."""
        # Test successful initialization
        result = self.kf.initialize(self.price_a, self.price_b)
        self.assertTrue(result)
        self.assertTrue(self.kf.is_initialized)
        
        # Test that hedge ratios are calculated
        self.assertIsNotNone(self.kf.hedge_ratios)
        self.assertEqual(len(self.kf.hedge_ratios), len(self.price_a))
        
        # Test that z-scores are calculated
        self.assertIsNotNone(self.kf.z_scores)
        self.assertEqual(len(self.kf.z_scores), len(self.price_a))
        
        # Test that spreads are calculated
        self.assertIsNotNone(self.kf.spreads)
        self.assertEqual(len(self.kf.spreads), len(self.price_a))
    
    def test_initialization_insufficient_data(self):
        """Test initialization with insufficient data."""
        short_price_a = self.price_a[:10]  # Only 10 points
        short_price_b = self.price_b[:10]
        
        result = self.kf.initialize(short_price_a, short_price_b)
        self.assertFalse(result)
        self.assertFalse(self.kf.is_initialized)
    
    def test_initialization_mismatched_lengths(self):
        """Test initialization with mismatched price series lengths."""
        price_a_short = self.price_a[:50]
        price_b_long = self.price_b[:60]
        
        result = self.kf.initialize(price_a_short, price_b_long)
        self.assertFalse(result)
        self.assertFalse(self.kf.is_initialized)
    
    def test_update(self):
        """Test Kalman Filter update with new data."""
        # Initialize first
        self.kf.initialize(self.price_a, self.price_b)
        
        # Test update with new prices
        new_price_a = 105.0
        new_price_b = 52.0
        
        hedge_ratio, z_score, spread = self.kf.update(new_price_a, new_price_b)
        
        # Check that values are reasonable
        self.assertIsInstance(hedge_ratio, float)
        self.assertIsInstance(z_score, float)
        self.assertIsInstance(spread, float)
        
        # Check that hedge ratio is reasonable (should be around 2 based on our synthetic data)
        self.assertGreater(hedge_ratio, 0.5)
        self.assertLess(hedge_ratio, 5.0)
        
        # Check that z-score is reasonable
        self.assertGreater(z_score, -10.0)
        self.assertLess(z_score, 10.0)
    
    def test_update_without_initialization(self):
        """Test update without prior initialization."""
        with self.assertRaises(RuntimeError):
            self.kf.update(100.0, 50.0)
    
    def test_get_current_state(self):
        """Test getting current state."""
        self.kf.initialize(self.price_a, self.price_b)
        
        state = self.kf.get_current_state()
        
        self.assertIn('hedge_ratio', state)
        self.assertIn('z_score', state)
        self.assertIn('spread', state)
        
        self.assertIsInstance(state['hedge_ratio'], float)
        self.assertIsInstance(state['z_score'], float)
        self.assertIsInstance(state['spread'], float)
    
    def test_get_historical_data(self):
        """Test getting historical data."""
        self.kf.initialize(self.price_a, self.price_b)
        
        historical = self.kf.get_historical_data()
        
        self.assertIn('hedge_ratios', historical)
        self.assertIn('z_scores', historical)
        self.assertIn('spreads', historical)
        
        self.assertEqual(len(historical['hedge_ratios']), len(self.price_a))
        self.assertEqual(len(historical['z_scores']), len(self.price_a))
        self.assertEqual(len(historical['spreads']), len(self.price_a))
    
    def test_reset(self):
        """Test reset functionality."""
        self.kf.initialize(self.price_a, self.price_b)
        self.assertTrue(self.kf.is_initialized)
        
        self.kf.reset()
        self.assertFalse(self.kf.is_initialized)
        self.assertIsNone(self.kf.hedge_ratios)
        self.assertIsNone(self.kf.z_scores)
        self.assertIsNone(self.kf.spreads)


class TestPairsTradingStrategy(unittest.TestCase):
    """Test cases for PairsTradingStrategy class."""
    
    def setUp(self):
        """Set up test data."""
        # Create synthetic price data
        np.random.seed(42)
        n_points = 100
        
        base_price_a = 100.0
        base_price_b = 50.0
        
        trend = np.linspace(0, 10, n_points)
        noise_a = np.random.normal(0, 1, n_points)
        noise_b = np.random.normal(0, 0.5, n_points)
        
        price_a = base_price_a + trend + noise_a
        price_b = base_price_b + 0.5 * trend + noise_b
        
        # Add mean reversion
        spread = price_a - 2 * price_b
        mean_reversion = -0.1 * (spread - np.mean(spread))
        price_a += mean_reversion
        
        self.price_a = pd.Series(price_a, index=pd.date_range('2024-01-01', periods=n_points, freq='D'))
        self.price_b = pd.Series(price_b, index=pd.date_range('2024-01-01', periods=n_points, freq='D'))
        
        # Initialize strategy
        self.strategy = PairsTradingStrategy(
            entry_threshold=2.0,
            exit_threshold=0.5,
            max_half_life_days=45
        )
    
    def test_initialization(self):
        """Test strategy initialization."""
        result = self.strategy.initialize(self.price_a, self.price_b)
        self.assertTrue(result)
        self.assertTrue(self.strategy.kalman_filter.is_initialized)
    
    def test_update_no_signal(self):
        """Test update when no signal should be generated."""
        self.strategy.initialize(self.price_a, self.price_b)
        
        # Use prices that should not generate a signal (z-score < entry_threshold)
        result = self.strategy.update(100.0, 50.0)
        
        self.assertIn('signal', result)
        self.assertEqual(result['signal'], 'NO_SIGNAL')
        self.assertIn('z_score', result)
        self.assertIn('hedge_ratio', result)
        self.assertIn('confidence', result)
    
    def test_update_with_signal(self):
        """Test update when a signal should be generated."""
        self.strategy.initialize(self.price_a, self.price_b)
        
        # Create extreme prices to trigger a signal
        # We'll use the last known hedge ratio to create an extreme z-score
        last_hedge_ratio = self.strategy.kalman_filter.hedge_ratios.iloc[-1]
        
        # Create a large spread to trigger signal
        extreme_price_a = 120.0  # Much higher than expected
        extreme_price_b = 50.0
        
        result = self.strategy.update(extreme_price_a, extreme_price_b)
        
        self.assertIn('signal', result)
        self.assertIn('z_score', result)
        self.assertIn('hedge_ratio', result)
        self.assertIn('confidence', result)
        
        # Signal might be NO_SIGNAL, ENTER_LONG_SPREAD, or ENTER_SHORT_SPREAD
        self.assertIn(result['signal'], ['NO_SIGNAL', 'ENTER_LONG_SPREAD', 'ENTER_SHORT_SPREAD', 'EXIT_POSITION'])
    
    def test_get_strategy_state(self):
        """Test getting strategy state."""
        self.strategy.initialize(self.price_a, self.price_b)
        
        state = self.strategy.get_strategy_state()
        
        self.assertIn('current_position', state)
        self.assertIn('position_entry_date', state)
        self.assertIn('position_entry_z_score', state)
        self.assertIn('kalman_state', state)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add tests
    test_suite.addTest(unittest.makeSuite(TestPairsKalmanFilter))
    test_suite.addTest(unittest.makeSuite(TestPairsTradingStrategy))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Test Results Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*50}")
    
    # Exit with appropriate code
    if result.failures or result.errors:
        sys.exit(1)
    else:
        print("All Python tests passed.")
        sys.exit(0)
