#include "position_tracker.h"
#include <iostream>
#include <iomanip>
#include <algorithm>
#include <cmath>

PositionTracker::PositionTracker() 
    : totalRealizedPnl_(0.0), totalUnrealizedPnl_(0.0), peakValue_(0.0), maxDrawdown_(0.0),
      dailyPnl_(0.0), dailyPeak_(0.0), dailyMaxDrawdown_(0.0) {
    
    lastDailyReset_ = std::chrono::system_clock::now();
    std::cout << "Position tracker initialized with PnL tracking" << std::endl;
}

PositionTracker::~PositionTracker() {
    std::cout << "Position tracker destroyed" << std::endl;
}

void PositionTracker::updatePosition(const std::string& symbol, const std::string& action, 
                                   int quantity, double price) {
    
    auto& position = positions_[symbol];
    position.lastUpdate = std::chrono::system_clock::now();
    
    if (action == "BUY") {
        if (position.quantity >= 0) {
            // Adding to long position or starting new long position
            double totalCost = position.quantity * position.avgPrice + quantity * price;
            position.quantity += quantity;
            position.avgPrice = (position.quantity > 0) ? totalCost / position.quantity : 0.0;
        } else {
            // Covering short position
            if (std::abs(position.quantity) >= quantity) {
                // Partial cover
                double realizedPnl = (position.avgPrice - price) * quantity;
                position.realizedPnl += realizedPnl;
                totalRealizedPnl_ += realizedPnl;
                position.quantity += quantity;
                
                if (position.quantity == 0) {
                    position.avgPrice = 0.0;
                }
            } else {
                // Full cover + new long position
                double coverQuantity = std::abs(position.quantity);
                double newLongQuantity = quantity - coverQuantity;
                
                // Realized P&L from covering short
                double realizedPnl = (position.avgPrice - price) * coverQuantity;
                position.realizedPnl += realizedPnl;
                totalRealizedPnl_ += realizedPnl;
                
                // Start new long position
                position.quantity = newLongQuantity;
                position.avgPrice = price;
            }
        }
    } else if (action == "SELL") {
        if (position.quantity <= 0) {
            // Adding to short position or starting new short position
            double totalCost = std::abs(position.quantity) * position.avgPrice + quantity * price;
            position.quantity -= quantity;
            position.avgPrice = (position.quantity < 0) ? totalCost / std::abs(position.quantity) : 0.0;
        } else {
            // Reducing long position
            if (position.quantity >= quantity) {
                // Partial sale
                double realizedPnl = (price - position.avgPrice) * quantity;
                position.realizedPnl += realizedPnl;
                totalRealizedPnl_ += realizedPnl;
                position.quantity -= quantity;
                
                if (position.quantity == 0) {
                    position.avgPrice = 0.0;
                }
            } else {
                // Full sale + new short position
                double saleQuantity = position.quantity;
                double newShortQuantity = quantity - saleQuantity;
                
                // Realized P&L from selling long
                double realizedPnl = (price - position.avgPrice) * saleQuantity;
                position.realizedPnl += realizedPnl;
                totalRealizedPnl_ += realizedPnl;
                
                // Start new short position
                position.quantity = -newShortQuantity;
                position.avgPrice = price;
            }
        }
    }
    
    // Update unrealized P&L and risk metrics
    updateUnrealizedPnl();
    updateDrawdownMetrics();
    updateDailyMetrics();
    
    std::cout << "Updated position for " << symbol << ": " << position.quantity 
              << " shares @ $" << std::fixed << std::setprecision(2) << position.avgPrice << std::endl;
}

void PositionTracker::updatePositions(const std::string& pairName, 
                                     const std::vector<OrderRequest>& orders) {
    for (const auto& order : orders) {
        // Note: This is called when orders are placed, not filled
        // Actual position updates happen in updatePosition() when orders are filled
        std::cout << "Order placed for " << pairName << ": " << order.action 
                  << " " << order.quantity << " " << order.symbol << std::endl;
    }
}

PairPositions PositionTracker::getPairPositions(const std::string& pairName) {
    // Extract symbol A and B from pair name (assuming format "SYMBOL_A_SYMBOL_B")
    size_t underscorePos = pairName.find('_');
    if (underscorePos == std::string::npos) {
        return PairPositions{pairName, 0, 0, 0.0, 0.0, 0.0, 0.0};
    }
    
    std::string symbolA = pairName.substr(0, underscorePos);
    std::string symbolB = pairName.substr(underscorePos + 1);
    
    PairPositions pairPos;
    pairPos.pairName = pairName;
    
    // Get position for symbol A
    if (positions_.find(symbolA) != positions_.end()) {
        const Position& posA = positions_[symbolA];
        pairPos.sharesA = posA.quantity;
        pairPos.avgPriceA = posA.avgPrice;
    } else {
        pairPos.sharesA = 0;
        pairPos.avgPriceA = 0.0;
    }
    
    // Get position for symbol B
    if (positions_.find(symbolB) != positions_.end()) {
        const Position& posB = positions_[symbolB];
        pairPos.sharesB = posB.quantity;
        pairPos.avgPriceB = posB.avgPrice;
    } else {
        pairPos.sharesB = 0;
        pairPos.avgPriceB = 0.0;
    }
    
    // Calculate market value and unrealized P&L
    double marketValueA = 0.0, marketValueB = 0.0;
    double unrealizedPnlA = 0.0, unrealizedPnlB = 0.0;
    
    if (positions_.find(symbolA) != positions_.end() && marketPrices_.find(symbolA) != marketPrices_.end()) {
        const Position& posA = positions_[symbolA];
        double currentPriceA = marketPrices_[symbolA];
        marketValueA = calculatePositionValue(posA, currentPriceA);
        unrealizedPnlA = posA.unrealizedPnl;
    }
    
    if (positions_.find(symbolB) != positions_.end() && marketPrices_.find(symbolB) != marketPrices_.end()) {
        const Position& posB = positions_[symbolB];
        double currentPriceB = marketPrices_[symbolB];
        marketValueB = calculatePositionValue(posB, currentPriceB);
        unrealizedPnlB = posB.unrealizedPnl;
    }
    
    pairPos.marketValue = marketValueA + marketValueB;
    pairPos.unrealizedPnl = unrealizedPnlA + unrealizedPnlB;
    
    return pairPos;
}

std::map<std::string, double> PositionTracker::getAllPositions() const {
    std::map<std::string, double> result;
    for (const auto& pair : positions_) {
        result[pair.first] = pair.second.quantity;
    }
    return result;
}

void PositionTracker::updateMarketPrices(const std::map<std::string, double>& prices) {
    marketPrices_ = prices;
    updateUnrealizedPnl();
    updateDrawdownMetrics();
    updateDailyMetrics();
}

double PositionTracker::getUnrealizedPnl(const std::string& symbol) const {
    if (positions_.find(symbol) == positions_.end()) {
        return 0.0;
    }
    return positions_.at(symbol).unrealizedPnl;
}

double PositionTracker::getTotalRealizedPnl() const {
    return totalRealizedPnl_;
}

double PositionTracker::getTotalUnrealizedPnl() const {
    return totalUnrealizedPnl_;
}

double PositionTracker::getTotalPnl() const {
    return totalRealizedPnl_ + totalUnrealizedPnl_;
}

double PositionTracker::getCurrentDrawdown() const {
    double currentValue = getTotalPnl();
    if (peakValue_ <= 0.0) return 0.0;
    return (peakValue_ - currentValue) / peakValue_ * 100.0;
}

double PositionTracker::getMaxDrawdown() const {
    return maxDrawdown_;
}

double PositionTracker::getPeakValue() const {
    return peakValue_;
}

double PositionTracker::getDailyPnl() const {
    return dailyPnl_;
}

double PositionTracker::getDailyDrawdown() const {
    return dailyMaxDrawdown_;
}

double PositionTracker::getPositionExposure() const {
    double totalExposure = 0.0;
    for (const auto& pair : positions_) {
        if (marketPrices_.find(pair.first) != marketPrices_.end()) {
            totalExposure += std::abs(calculatePositionValue(pair.second, marketPrices_.at(pair.first)));
        }
    }
    return totalExposure;
}

double PositionTracker::getLeverage() const {
    // Simplified leverage calculation
    double exposure = getPositionExposure();
    double totalPnl = getTotalPnl();
    return (exposure > 0.0) ? exposure / (exposure + totalPnl) : 0.0;
}

void PositionTracker::addPnLHistory() {
    PnLHistory history;
    history.totalPnl = getTotalPnl();
    history.realizedPnl = getTotalRealizedPnl();
    history.unrealizedPnl = getTotalUnrealizedPnl();
    history.drawdown = getCurrentDrawdown();
    history.peakValue = getPeakValue();
    history.timestamp = std::chrono::system_clock::now();
    
    pnlHistory_.push_back(history);
    clearOldHistory();
}

std::vector<PnLHistory> PositionTracker::getPnLHistory() const {
    return std::vector<PnLHistory>(pnlHistory_.begin(), pnlHistory_.end());
}

void PositionTracker::clearOldHistory(int maxEntries) {
    while (pnlHistory_.size() > maxEntries) {
        pnlHistory_.pop_front();
    }
}

bool PositionTracker::isDrawdownLimitExceeded(double maxDrawdownPercent) const {
    return getCurrentDrawdown() > maxDrawdownPercent;
}

bool PositionTracker::isDailyLossLimitExceeded(double maxDailyLoss) const {
    return dailyPnl_ < -maxDailyLoss;
}

bool PositionTracker::isExposureLimitExceeded(double maxExposure) const {
    return getPositionExposure() > maxExposure;
}

void PositionTracker::printPositions() const {
    std::cout << "\n=== Current Positions ===" << std::endl;
    for (const auto& pair : positions_) {
        const Position& pos = pair.second;
        std::cout << std::left << std::setw(10) << pair.first 
                  << std::right << std::setw(8) << pos.quantity 
                  << " @ $" << std::fixed << std::setprecision(2) << pos.avgPrice
                  << " | Realized: $" << std::setw(10) << pos.realizedPnl
                  << " | Unrealized: $" << std::setw(10) << pos.unrealizedPnl << std::endl;
    }
    std::cout << "========================\n" << std::endl;
}

void PositionTracker::printPnLSummary() const {
    std::cout << "\n=== P&L Summary ===" << std::endl;
    std::cout << "Total Realized P&L: $" << std::fixed << std::setprecision(2) << getTotalRealizedPnl() << std::endl;
    std::cout << "Total Unrealized P&L: $" << getTotalUnrealizedPnl() << std::endl;
    std::cout << "Total P&L: $" << getTotalPnl() << std::endl;
    std::cout << "Peak Value: $" << getPeakValue() << std::endl;
    std::cout << "Current Drawdown: " << std::fixed << std::setprecision(2) << getCurrentDrawdown() << "%" << std::endl;
    std::cout << "Max Drawdown: " << getMaxDrawdown() << "%" << std::endl;
    std::cout << "==================\n" << std::endl;
}

void PositionTracker::printRiskMetrics() const {
    std::cout << "\n=== Risk Metrics ===" << std::endl;
    std::cout << "Daily P&L: $" << std::fixed << std::setprecision(2) << getDailyPnl() << std::endl;
    std::cout << "Daily Max Drawdown: " << getDailyDrawdown() << "%" << std::endl;
    std::cout << "Position Exposure: $" << getPositionExposure() << std::endl;
    std::cout << "Leverage: " << std::fixed << std::setprecision(2) << getLeverage() << std::endl;
    std::cout << "==================\n" << std::endl;
}

void PositionTracker::resetDaily() {
    dailyPnl_ = 0.0;
    dailyPeak_ = 0.0;
    dailyMaxDrawdown_ = 0.0;
    lastDailyReset_ = std::chrono::system_clock::now();
    std::cout << "Daily metrics reset" << std::endl;
}

void PositionTracker::resetAll() {
    positions_.clear();
    marketPrices_.clear();
    totalRealizedPnl_ = 0.0;
    totalUnrealizedPnl_ = 0.0;
    peakValue_ = 0.0;
    maxDrawdown_ = 0.0;
    dailyPnl_ = 0.0;
    dailyPeak_ = 0.0;
    dailyMaxDrawdown_ = 0.0;
    pnlHistory_.clear();
    lastDailyReset_ = std::chrono::system_clock::now();
    std::cout << "All position and P&L data reset" << std::endl;
}

void PositionTracker::updateUnrealizedPnl() {
    totalUnrealizedPnl_ = 0.0;
    
    for (auto& pair : positions_) {
        Position& pos = pair.second;
        const std::string& symbol = pair.first;
        
        if (marketPrices_.find(symbol) != marketPrices_.end()) {
            double currentPrice = marketPrices_[symbol];
            pos.marketValue = calculatePositionValue(pos, currentPrice);
            
            if (pos.quantity > 0) {
                // Long position
                pos.unrealizedPnl = (currentPrice - pos.avgPrice) * pos.quantity;
            } else if (pos.quantity < 0) {
                // Short position
                pos.unrealizedPnl = (pos.avgPrice - currentPrice) * std::abs(pos.quantity);
            } else {
                pos.unrealizedPnl = 0.0;
            }
            
            totalUnrealizedPnl_ += pos.unrealizedPnl;
        }
    }
}

void PositionTracker::updateDrawdownMetrics() {
    double currentValue = getTotalPnl();
    
    // Update peak value
    if (currentValue > peakValue_) {
        peakValue_ = currentValue;
    }
    
    // Update max drawdown
    if (peakValue_ > 0.0) {
        double currentDrawdown = (peakValue_ - currentValue) / peakValue_ * 100.0;
        if (currentDrawdown > maxDrawdown_) {
            maxDrawdown_ = currentDrawdown;
        }
    }
}

void PositionTracker::updateDailyMetrics() {
    auto now = std::chrono::system_clock::now();
    auto timeSinceReset = std::chrono::duration_cast<std::chrono::hours>(now - lastDailyReset_).count();
    
    // Reset daily metrics if more than 24 hours have passed
    if (timeSinceReset >= 24) {
        resetDaily();
    }
    
    double currentPnl = getTotalPnl();
    dailyPnl_ = currentPnl;
    
    // Update daily peak and drawdown
    if (currentPnl > dailyPeak_) {
        dailyPeak_ = currentPnl;
    }
    
    if (dailyPeak_ > 0.0) {
        double dailyDrawdown = (dailyPeak_ - currentPnl) / dailyPeak_ * 100.0;
        if (dailyDrawdown > dailyMaxDrawdown_) {
            dailyMaxDrawdown_ = dailyDrawdown;
        }
    }
}

double PositionTracker::calculatePositionValue(const Position& pos, double currentPrice) const {
    return pos.quantity * currentPrice;
}
