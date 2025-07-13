#pragma once

#include <string>
#include "signal_parser.h"
#include "order_manager.h"

class RiskChecker {
public:
    RiskChecker();
    ~RiskChecker();
    
    // Set risk limits
    void setRiskLimits(double maxPositionSize, double maxDailyLoss, 
                      double maxTotalExposure, double minConfidence, 
                      double maxZScore, double maxDrawdownPercent = 10.0);
    
    // Check risk for signals and orders
    bool checkSignalRisk(const TradeSignal& signal);
    bool checkOrderRisk(const OrderRequest& order);
    
    // Update risk metrics
    void updateDailyPnl(double pnl);
    void updateTotalExposure(double exposure);
    void updateDrawdown(double drawdownPercent);
    void resetDaily();
    
    // Check if trading is allowed
    bool isTradingAllowed() const;
    
    // Display risk status
    void printRiskStatus() const;
    
private:
    // Risk limits
    double maxPositionSize_;
    double maxDailyLoss_;
    double maxTotalExposure_;
    double minConfidence_;
    double maxZScore_;
    double maxDrawdownPercent_;
    
    // Current risk metrics
    double dailyPnl_;
    double totalExposure_;
    double currentDrawdown_;
}; 