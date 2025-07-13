# Algorithmic Pairs Trading System

A hybrid Python/C++ algorithmic trading system implementing statistical arbitrage strategies with real-time market data processing and low-latency order execution.

## Overview

This system implements a pairs trading strategy using Kalman Filter-based dynamic hedge ratio estimation. The architecture separates concerns between Python (data processing, signal generation) and C++ (order execution, risk management) for optimal performance.

### Key Features

- **Hybrid Architecture**: Python data engine + C++ order execution engine
- **Real-Time Processing**: Microsecond-latency ZeroMQ communication
- **Trading Algorithms**: Kalman Filter for dynamic hedge ratio estimation
- **Brokerage Integration**: Interactive Brokers TWS API
- **Risk Management**: Comprehensive position tracking and risk controls
- **Production/Deployment**: Configuration management, logging, monitoring

## Project Architecture

```
┌────────────────────────┐    ZeroMQ    ┌───────────────────────┐
│   Python Data          │ ───────────> │  C++ Order            │
│     Engine             │              │   Engine              │
│                        │              │                       │
│ • Market Data          │              │ • Order Management    │
│ • Signal Generation    │              │ • Risk Checks         │
│ • Kalman Filtering     │              │ • Position Tracking   │
└────────────────────────┘              └───────────────────────┘
         ^                                      │
         │                                      │
         │                                      v
┌─────────────────┐                     ┌─────────────────────┐
│ Interactive     │                     │ TWS API             │
│ Brokers API     │                     │ (Order Execution)   │
│  (Market Data)  │                     └─────────────────────┘
└─────────────────┘                     
```

## Quick Start

### Prerequisites

- **Python 3.8+**
- **C++17 compatible compiler** (GCC 7+, Clang 5+, MSVC 2017+)
- **Interactive Brokers TWS** (Paper Trading recommended for testing)
- **CMake 3.15+**

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AlgoTrading_TWSCPP
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Build C++ components**
   ```bash
   mkdir build && cd build
   cmake ..
   make -j4
   ```

4. **Configure TWS**
   - Enable API connections in TWS
   - Set port to 7497 (paper trading) or 7496 (live)
   - Allow connections from localhost

5. **Update configuration**
   ```bash
   # Edit config/trading_config.yaml for your settings
   # Set your allocated capital, risk parameters, etc.
   ```

### Running the System

```bash
# Start the complete trading system
python run_trading_system.py

# Or run components separately
python python/main_data_engine.py  # Data engine only
./build/trading_engine             # C++ engine only
```

## Strategy Details

### Pairs Trading with Kalman Filter

The system implements statistical arbitrage using:

- **Dynamic Hedge Ratios**: Kalman Filter estimates optimal hedge ratios in real-time
- **Z-Score Based Signals**: Entry/exit based on statistical deviations
- **Half-Life Screening**: Prevents trading on mean-reverting pairs with long half-lives
- **Risk Management**: Position sizing, correlation monitoring, drawdown protection

### Signal Generation Process

1. **Data Ingestion**: Real-time market data from Interactive Brokers
2. **Kalman Filter Update**: Dynamic hedge ratio estimation
3. **Z-Score Calculation**: Statistical deviation measurement
4. **Signal Generation**: Entry/exit decisions based on thresholds
5. **Risk Validation**: Position sizing and risk checks

### Order Execution Flow

1. **Signal Reception**: C++ engine receives signals via ZeroMQ
2. **Risk Validation**: Position limits, margin requirements
3. **Order Creation**: Market orders for both legs of the spread
4. **Execution**: TWS API order placement and monitoring
5. **Position Tracking**: Real-time position and P&L updates

## Configuration

### Trading Parameters

```yaml
strategy:
  entry_threshold: 0.25     # Z-score for entry
  exit_threshold: 0.25      # Z-score for exit
  max_half_life_days: 45    # Maximum half-life
  
kalman:
  observation_covariance: 0.001
  delta: 0.0001
  initial_state_covariance: 1.0

risk:
  allocated_capital: 35000   # Capital per position
  max_position_size: 1000    # Max shares
```

### Risk Management

- **Position Limits**: Maximum position sizes per pair
- **Correlation Monitoring**: Automatic pair breakdown detection
- **Drawdown Protection**: Stop-loss mechanisms
- **Margin Monitoring**: Real-time margin requirement tracking

## Testing

### Unit Tests

```bash
# Python tests
python -m pytest tests/python/

# C++ tests
cd build && make test
```

### Integration Tests

```bash
# Test complete system
python test_live_trading.py

# Quick order execution test
python quick_order_test.py
```

### Latency Testing

```bash
# Measure system latency
python run_latency_test.py
```

## Performance

### Latency Details

- **End-to-End Latency (market data to order placement)** 5.63ms when tested on my system
## Development

### Project Structure

```
AlgoTrading_TWSCPP/
├── python/                 # Python data engine
│   ├── strategy/          # Trading strategies
│   ├── data_engine/       # Market data processing
│   ├── comms/             # ZeroMQ communication
│   └── monitoring/        # Performance monitoring
├── cpp/                   # C++ order execution engine
│   ├── src/              # Source files
│   ├── include/          # Header files
│   └── tests/            # C++ tests
├── config/               # Configuration files
├── tests/                # Integration tests
├── logs/                 # System logs
└── backtest.ipynb        # Jupyter Notebook with Custom Backtesting Framework
```

### Adding New Strategies

1. **Create strategy class** in `python/strategy/`
2. **Implement signal generation** logic
3. **Add configuration** in `config/trading_config.yaml`
4. **Update signal parser** in C++ if needed
5. **Add tests** for validation

### Extending Order Types

1. **Modify OrderManager** in C++
2. **Update OrderUtils** for new order types
3. **Add risk checks** as needed
4. **Test with paper trading**

## Risk Disclaimer

**This software is for educational and research purposes only. Trading involves substantial risk of loss and is not suitable for all investors. Past performance does not guarantee future results.**

- Always test with paper trading first
- Start with small position sizes
- Monitor system performance continuously
- Understand the risks of algorithmic trading
- Ensure compliance with local regulations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Technical Highlights

### Advanced Algorithms
- **Kalman Filter**: Dynamic hedge ratio estimation
- **Statistical Arbitrage**: Mean-reversion based trading
- **Half-Life Analysis**: Pair stability assessment

### Performance Optimization
- **ZeroMQ**: High-performance messaging
- **C++ Order Engine**: Low-latency execution
- **Memory Management**: Efficient data structures

### Production Features
- **Comprehensive Logging**: Structured logging with rotation
- **Configuration Management**: YAML-based configuration
- **Error Handling**: Robust error recovery
- **Monitoring**: Performance metrics and alerts

### Brokerage Integration
- **Interactive Brokers API**: Industry-standard trading platform
- **Real-Time Data**: Live market data streaming
