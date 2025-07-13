#pragma once

#include <string>
#include <map>
#include <vector>
#include <deque>
#include <chrono>
#include "order_manager.h"

struct Position {
    int quantity;
    double avgPrice;
    double realizedPnl;
    double unrealizedPnl;
    double marketValue;
    std::chrono::system_clock::time_point lastUpdate;
    
    Position() : quantity(0), avgPrice(0.0), realizedPnl(0.0), 
                 unrealizedPnl(0.0), marketValue(0.0) {}
};

struct PnLHistory {
    double totalPnl;
    double realizedPnl;
    double unrealizedPnl;
    double drawdown;
    double peakValue;
    std::chrono::system_clock::time_point timestamp;
    
    PnLHistory() : totalPnl(0.0), realizedPnl(0.0), unrealizedPnl(0.0), 
                   drawdown(0.0), peakValue(0.0) {}
};

class PositionTracker {
public:
    PositionTracker();
    ~PositionTracker();
    
    // Update position when orders are filled
    void updatePosition(const std::string& symbol, const std::string& action, 
                       int quantity, double price);
    
    // Track orders for a pair
    void updatePositions(const std::string& pairName, 
                        const std::vector<OrderRequest>& orders);
    
    // Get positions for a specific pair
    PairPositions getPairPositions(const std::string& pairName);
    
    // Get all current positions
    std::map<std::string, double> getAllPositions() const;
    
    // Update market prices for P&L calculations
    void updateMarketPrices(const std::map<std::string, double>& prices);
    
    // P&L calculations
    double getUnrealizedPnl(const std::string& symbol) const;
    double getTotalRealizedPnl() const;
    double getTotalUnrealizedPnl() const;
    double getTotalPnl() const;
    
    // Drawdown tracking
    double getCurrentDrawdown() const;
    double getMaxDrawdown() const;
    double getPeakValue() const;
    
    // Risk metrics
    double getDailyPnl() const;
    double getDailyDrawdown() const;
    double getPositionExposure() const;
    double getLeverage() const;
    
    // Historical tracking
    void addPnLHistory();
    std::vector<PnLHistory> getPnLHistory() const;
    void clearOldHistory(int maxEntries = 1000);
    
    // Risk management
    bool isDrawdownLimitExceeded(double maxDrawdownPercent) const;
    bool isDailyLossLimitExceeded(double maxDailyLoss) const;
    bool isExposureLimitExceeded(double maxExposure) const;
    
    // Display positions and P&L
    void printPositions() const;
    void printPnLSummary() const;
    void printRiskMetrics() const;
    
    // Reset functions
    void resetDaily();
    void resetAll();
    
private:
    std::map<std::string, Position> positions_;
    std::map<std::string, double> marketPrices_;
    
    // P&L tracking
    double totalRealizedPnl_;
    double totalUnrealizedPnl_;
    double peakValue_;
    double maxDrawdown_;
    
    // Daily tracking
    double dailyPnl_;
    double dailyPeak_;
    double dailyMaxDrawdown_;
    std::chrono::system_clock::time_point lastDailyReset_;
    
    // Historical data
    std::deque<PnLHistory> pnlHistory_;
    
    // Helper functions
    void updateUnrealizedPnl();
    void updateDrawdownMetrics();
    void updateDailyMetrics();
    double calculatePositionValue(const Position& pos, double currentPrice) const;
};
