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