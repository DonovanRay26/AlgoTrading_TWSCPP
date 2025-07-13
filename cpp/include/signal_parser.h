#pragma once

#include <string>
#include "simple_json_parser.h"

enum class MessageType {
    TRADE_SIGNAL,
    POSITION_UPDATE,
    PERFORMANCE_UPDATE,
    SYSTEM_STATUS,
    ERROR_MESSAGE,
    HEARTBEAT,
    UNKNOWN
};

struct TradeSignal {
    std::string messageId;
    std::string timestamp;
    std::string pairName;
    std::string symbolA;
    std::string symbolB;
    std::string signalType;
    double zScore;
    double hedgeRatio;
    double confidence;
    int positionSize;
    int sharesA;
    int sharesB;
    double volatility;
    double correlation;
};

struct PositionUpdate {
    std::string messageId;
    std::string timestamp;
    std::string pairName;
    std::string symbolA;
    std::string symbolB;
    std::string currentPosition;
    int sharesA;
    int sharesB;
    double marketValue;
    double unrealizedPnl;
    double priceA;
    double priceB;
};

struct PerformanceUpdate {
    std::string messageId;
    std::string timestamp;
    double totalPnl;
    double dailyPnl;
    double totalReturn;
    double sharpeRatio;
    double maxDrawdown;
    int totalPositions;
    int activePairs;
    double cashBalance;
};

struct SystemStatus {
    std::string messageId;
    std::string timestamp;
    std::string status;
    std::string component;
    double uptimeSeconds;
    double memoryUsageMb;
    double cpuUsagePercent;
    std::string message;
};

struct ErrorMessage {
    std::string messageId;
    std::string timestamp;
    std::string errorType;
    std::string errorCode;
    std::string errorMessage;
    std::string severity;
    std::string component;
    std::string pairName;
};

class SignalParser {
public:
    SignalParser();
    
    // Parse different message types
    TradeSignal parseTradeSignal(const std::string& jsonStr);
    PositionUpdate parsePositionUpdate(const std::string& jsonStr);
    PerformanceUpdate parsePerformanceUpdate(const std::string& jsonStr);
    SystemStatus parseSystemStatus(const std::string& jsonStr);
    ErrorMessage parseErrorMessage(const std::string& jsonStr);
    
    // Utility functions
    MessageType getMessageType(const std::string& jsonStr);
    bool isValidMessage(const std::string& jsonStr);
}; 