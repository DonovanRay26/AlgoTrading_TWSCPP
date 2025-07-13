#include "risk_checker.h"
#include <iostream>
#include <cmath>

RiskChecker::RiskChecker() {
    // Initialize default risk limits
    maxPositionSize_ = 10000;  // Maximum shares per position
    maxDailyLoss_ = 5000.0;    // Maximum daily loss in dollars
    maxTotalExposure_ = 100000.0;  // Maximum total exposure in dollars
    minConfidence_ = 0.7;      // Minimum confidence for signal execution
    maxZScore_ = 3.0;          // Maximum z-score for signal execution
    maxDrawdownPercent_ = 10.0; // Maximum drawdown percentage
    
    dailyPnl_ = 0.0;
    totalExposure_ = 0.0;
    
    std::cout << "Risk checker initialized with enhanced limits" << std::endl;
}

RiskChecker::~RiskChecker() {
    std::cout << "Risk checker destroyed" << std::endl;
}

void RiskChecker::setRiskLimits(double maxPositionSize, double maxDailyLoss, 
                               double maxTotalExposure, double minConfidence, 
                               double maxZScore, double maxDrawdownPercent) {
    maxPositionSize_ = maxPositionSize;
    maxDailyLoss_ = maxDailyLoss;
    maxTotalExposure_ = maxTotalExposure;
    minConfidence_ = minConfidence;
    maxZScore_ = maxZScore;
    maxDrawdownPercent_ = maxDrawdownPercent;
    
    std::cout << "Risk limits updated:" << std::endl;
    std::cout << "  Max Position Size: " << maxPositionSize_ << " shares" << std::endl;
    std::cout << "  Max Daily Loss: $" << maxDailyLoss_ << std::endl;
    std::cout << "  Max Total Exposure: $" << maxTotalExposure_ << std::endl;
    std::cout << "  Min Confidence: " << minConfidence_ << std::endl;
    std::cout << "  Max Z-Score: " << maxZScore_ << std::endl;
    std::cout << "  Max Drawdown: " << maxDrawdownPercent_ << "%" << std::endl;
}

bool RiskChecker::checkSignalRisk(const TradeSignal& signal) {
    std::cout << "Checking risk for signal: " << signal.signalType << std::endl;
    
    // Check confidence threshold
    if (signal.confidence < minConfidence_) {
        std::cout << "Signal rejected: Confidence " << signal.confidence 
                  << " below minimum " << minConfidence_ << std::endl;
        return false;
    }
    
    // Check z-score threshold
    if (std::abs(signal.zScore) > maxZScore_) {
        std::cout << "Signal rejected: Z-score " << signal.zScore 
                  << " exceeds maximum " << maxZScore_ << std::endl;
        return false;
    }
    
    // Check position size limits
    if (std::abs(signal.sharesA) > maxPositionSize_) {
        std::cout << "Signal rejected: Shares A " << signal.sharesA 
                  << " exceeds maximum " << maxPositionSize_ << std::endl;
        return false;
    }
    
    if (std::abs(signal.sharesB) > maxPositionSize_) {
        std::cout << "Signal rejected: Shares B " << signal.sharesB 
                  << " exceeds maximum " << maxPositionSize_ << std::endl;
        return false;
    }
    
    // Check daily loss limit
    if (dailyPnl_ < -maxDailyLoss_) {
        std::cout << "Signal rejected: Daily loss $" << -dailyPnl_ 
                  << " exceeds maximum $" << maxDailyLoss_ << std::endl;
        return false;
    }
    
    // Check total exposure limit
    double signalExposure = std::abs(signal.sharesA) + std::abs(signal.sharesB);
    if (totalExposure_ + signalExposure > maxTotalExposure_) {
        std::cout << "Signal rejected: Total exposure " << (totalExposure_ + signalExposure)
                  << " would exceed maximum " << maxTotalExposure_ << std::endl;
        return false;
    }
    
    // Check for excessive correlation
    if (signal.correlation > 0.95 || signal.correlation < -0.95) {
        std::cout << "Signal rejected: Correlation " << signal.correlation 
                  << " is too extreme" << std::endl;
        return false;
    }
    
    // Check for excessive volatility
    if (signal.volatility > 0.5) {  // 50% volatility threshold
        std::cout << "Signal rejected: Volatility " << signal.volatility 
                  << " is too high" << std::endl;
        return false;
    }
    
    std::cout << "Signal passed all risk checks" << std::endl;
    return true;
}

bool RiskChecker::checkOrderRisk(const OrderRequest& order) {
    std::cout << "Checking order risk for " << order.symbol << std::endl;
    
    // Check position size limit
    if (order.quantity > maxPositionSize_) {
        std::cout << "Order rejected: Quantity " << order.quantity 
                  << " exceeds maximum " << maxPositionSize_ << std::endl;
        return false;
    }
    
    // Check if this would exceed total exposure
    if (totalExposure_ + order.quantity > maxTotalExposure_) {
        std::cout << "Order rejected: Would exceed total exposure limit" << std::endl;
        return false;
    }
    
    std::cout << "Order passed risk checks" << std::endl;
    return true;
}

void RiskChecker::updateDailyPnl(double pnl) {
    dailyPnl_ = pnl;
    
    std::cout << "Updated daily P&L: $" << dailyPnl_ << std::endl;
    
    // Check if we've hit daily loss limit
    if (dailyPnl_ < -maxDailyLoss_) {
        std::cout << "WARNING: Daily loss limit exceeded!" << std::endl;
    }
}

void RiskChecker::updateTotalExposure(double exposure) {
    totalExposure_ = exposure;
    
    std::cout << "Updated total exposure: $" << totalExposure_ << std::endl;
    
    // Check if we're approaching exposure limit
    if (totalExposure_ > maxTotalExposure_ * 0.9) {
        std::cout << "WARNING: Approaching total exposure limit!" << std::endl;
    }
}

void RiskChecker::updateDrawdown(double drawdownPercent) {
    currentDrawdown_ = drawdownPercent;
    
    std::cout << "Updated current drawdown: " << currentDrawdown_ << "%" << std::endl;
    
    // Check if we've hit drawdown limit
    if (currentDrawdown_ > maxDrawdownPercent_) {
        std::cout << "WARNING: Maximum drawdown limit exceeded!" << std::endl;
    }
}

void RiskChecker::resetDaily() {
    dailyPnl_ = 0.0;
    std::cout << "Daily P&L reset to $0.00" << std::endl;
}

bool RiskChecker::isTradingAllowed() const {
    // Check if trading should be halted due to risk limits
    if (dailyPnl_ < -maxDailyLoss_) {
        std::cout << "Trading halted: Daily loss limit exceeded" << std::endl;
        return false;
    }
    
    if (totalExposure_ > maxTotalExposure_) {
        std::cout << "Trading halted: Total exposure limit exceeded" << std::endl;
        return false;
    }
    
    if (currentDrawdown_ > maxDrawdownPercent_) {
        std::cout << "Trading halted: Maximum drawdown limit exceeded" << std::endl;
        return false;
    }
    
    return true;
}

void RiskChecker::printRiskStatus() const {
    std::cout << "\n=== Risk Status ===" << std::endl;
    std::cout << "Daily P&L: $" << dailyPnl_ << " (Limit: $" << maxDailyLoss_ << ")" << std::endl;
    std::cout << "Total Exposure: $" << totalExposure_ << " (Limit: $" << maxTotalExposure_ << ")" << std::endl;
    std::cout << "Current Drawdown: " << currentDrawdown_ << "% (Limit: " << maxDrawdownPercent_ << "%)" << std::endl;
    std::cout << "Max Position Size: " << maxPositionSize_ << " shares" << std::endl;
    std::cout << "Min Confidence: " << minConfidence_ << std::endl;
    std::cout << "Max Z-Score: " << maxZScore_ << std::endl;
    std::cout << "Trading Allowed: " << (isTradingAllowed() ? "Yes" : "No") << std::endl;
    std::cout << "==================\n" << std::endl;
} 