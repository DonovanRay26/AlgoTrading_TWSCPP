# Algorithmic Trading with IBKR's TWS on C++

This project aims to achieve low-latency trading using C++ through Interactive Broker's Trader Workstation API

## Current State

As of right now this project:
 - Successfully includes IBKR's TWSAPI for C++
 - Resolves out-of-date aspects of the API code (stubbed out decimal operations in Decimal.cpp)
 - Overwrites EWrapper functions that will be needed during trading in MyWrapper.h
 - Connects to TWS in main.cpp


## Next Steps

My next steps are to:
 - Research a trading strategy, likely a mean-reversion strategy with inspiration from Ernest Chan's Algorithmic Trading
 - Backtest trading strategy
 - Deploy trading strategy on a paper trading account for live-testing

 ## Dependencies

- ✅ [Interactive Brokers C++ API](https://interactivebrokers.github.io/)
- ✅ Visual Studio 2019+ or g++ (for Linux)
- ✅ CMake 3.10 or higher

Ensure TWS or IB Gateway is installed and running, with API access enabled:
- IB TWS: `Edit → Global Configuration → API → Settings`
- Enable `Socket clients` and set port (default: `7496` for TWS, `4001` for IB Gateway)

---

## Build Instructions

### Windows (Visual Studio + CMake)

1. Clone this repository:
    ```bash
    git clone https://github.com/yourusername/AlgoTrading_TWSCPP.git
    cd AlgoTrading_TWSCPP
    ```

2. Modify the `CMakeLists.txt` to point to your TWS API source path (or copy all API `.cpp` and `.h` files into the project).

3. Build:
    ```bash
    mkdir build
    cd build
    cmake ..
    cmake --build .
    ```

4. Run the executable:
    ```bash
    ./Debug/TWSConnect.exe
    ```

---

## Disclaimer

> This project is for **educational and research purposes only**. Trading involves substantial risk and is not suitable for every investor. Use at your own discretion.

---

## License

MIT License

---