#pragma once

#include <string>
#include <regex>
#include <vector>

class Validation {
public:
    // Symbol validation
    static bool isValidSymbol(const std::string& symbol);
    static bool isValidPairName(const std::string& pairName);
    
    // Price validation
    static bool isValidPrice(double price);
    static bool isValidQuantity(int quantity);
    
    // Signal validation
    static bool isValidConfidence(double confidence);
    static bool isValidZScore(double zScore);
    static bool isValidHedgeRatio(double hedgeRatio);
    
    // Message validation
    static bool isValidMessageId(const std::string& messageId);
    static bool isValidTimestamp(const std::string& timestamp);
    
    // Order validation
    static bool isValidOrderType(const std::string& orderType);
    static bool isValidAction(const std::string& action);
    
    // Risk validation
    static bool isValidRiskLimits(double maxPositionSize, double maxDailyLoss, 
                                 double maxTotalExposure, double minConfidence, double maxZScore);
    
    // Network validation
    static bool isValidHost(const std::string& host);
    static bool isValidPort(int port);
    
private:
    static const std::regex SYMBOL_REGEX;
    static const std::regex PAIR_NAME_REGEX;
    static const std::regex MESSAGE_ID_REGEX;
    static const std::regex TIMESTAMP_REGEX;
    
    static const double MIN_PRICE;
    static const double MAX_PRICE;
    static const int MIN_QUANTITY;
    static const int MAX_QUANTITY;
    static const double MIN_CONFIDENCE;
    static const double MAX_CONFIDENCE;
    static const double MIN_Z_SCORE;
    static const double MAX_Z_SCORE;
    static const int MIN_PORT;
    static const int MAX_PORT;
}; 