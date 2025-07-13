#include "signal_parser.h"
#include <iostream>
#include <sstream>
#include <stdexcept>

SignalParser::SignalParser() {
    // Initialize JSON parser
}

TradeSignal SignalParser::parseTradeSignal(const std::string& jsonStr) {
    try {
        // Parse JSON string to extract trade signal data
        auto j = SimpleJsonParser::parse(jsonStr);
        
        TradeSignal signal;
        signal.messageId = j["message_id"].asString();
        signal.timestamp = j["timestamp"].asString();
        signal.pairName = j["pair_name"].asString();
        signal.symbolA = j["symbol_a"].asString();
        signal.symbolB = j["symbol_b"].asString();
        signal.signalType = j["signal_type"].asString();
        signal.zScore = j["z_score"].asDouble();
        signal.hedgeRatio = j["hedge_ratio"].asDouble();
        signal.confidence = j["confidence"].asDouble();
        signal.positionSize = j["position_size"].asInt();
        signal.sharesA = j["shares_a"].asInt();
        signal.sharesB = j["shares_b"].asInt();
        signal.volatility = j["volatility"].asDouble();
        signal.correlation = j["correlation"].asDouble();
        
        return signal;
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to parse trade signal: " + std::string(e.what()));
    }
}

PositionUpdate SignalParser::parsePositionUpdate(const std::string& jsonStr) {
    try {
        auto j = SimpleJsonParser::parse(jsonStr);
        
        PositionUpdate update;
        update.messageId = j["message_id"].asString();
        update.timestamp = j["timestamp"].asString();
        update.pairName = j["pair_name"].asString();
        update.symbolA = j["symbol_a"].asString();
        update.symbolB = j["symbol_b"].asString();
        update.currentPosition = j["current_position"].asString();
        update.sharesA = j["shares_a"].asInt();
        update.sharesB = j["shares_b"].asInt();
        update.marketValue = j["market_value"].asDouble();
        update.unrealizedPnl = j["unrealized_pnl"].asDouble();
        update.priceA = j["price_a"].asDouble();
        update.priceB = j["price_b"].asDouble();
        
        return update;
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to parse position update: " + std::string(e.what()));
    }
}

PerformanceUpdate SignalParser::parsePerformanceUpdate(const std::string& jsonStr) {
    try {
        auto j = SimpleJsonParser::parse(jsonStr);
        
        PerformanceUpdate update;
        update.messageId = j["message_id"].asString();
        update.timestamp = j["timestamp"].asString();
        update.totalPnl = j["total_pnl"].asDouble();
        update.dailyPnl = j["daily_pnl"].asDouble();
        update.totalReturn = j["total_return"].asDouble();
        update.sharpeRatio = j["sharpe_ratio"].asDouble();
        update.maxDrawdown = j["max_drawdown"].asDouble();
        update.totalPositions = j["total_positions"].asInt();
        update.activePairs = j["active_pairs"].asInt();
        update.cashBalance = j["cash_balance"].asDouble();
        
        return update;
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to parse performance update: " + std::string(e.what()));
    }
}

SystemStatus SignalParser::parseSystemStatus(const std::string& jsonStr) {
    try {
        auto j = SimpleJsonParser::parse(jsonStr);
        
        SystemStatus status;
        status.messageId = j["message_id"].asString();
        status.timestamp = j["timestamp"].asString();
        status.status = j["status"].asString();
        status.component = j["component"].asString();
        status.uptimeSeconds = j["uptime_seconds"].asDouble();
        status.memoryUsageMb = j["memory_usage_mb"].asDouble();
        status.cpuUsagePercent = j["cpu_usage_percent"].asDouble();
        status.message = j["message"].asString();
        
        return status;
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to parse system status: " + std::string(e.what()));
    }
}

ErrorMessage SignalParser::parseErrorMessage(const std::string& jsonStr) {
    try {
        auto j = SimpleJsonParser::parse(jsonStr);
        
        ErrorMessage error;
        error.messageId = j["message_id"].asString();
        error.timestamp = j["timestamp"].asString();
        error.errorType = j["error_type"].asString();
        error.errorCode = j["error_code"].asString();
        error.errorMessage = j["error_message"].asString();
        error.severity = j["severity"].asString();
        error.component = j["component"].asString();
        
        if (j.contains("pair_name")) {
            error.pairName = j["pair_name"].asString();
        }
        
        return error;
    } catch (const std::exception& e) {
        throw std::runtime_error("Failed to parse error message: " + std::string(e.what()));
    }
}

MessageType SignalParser::getMessageType(const std::string& jsonStr) {
    try {
        auto j = SimpleJsonParser::parse(jsonStr);
        std::string messageType = j["message_type"].asString();
        
        if (messageType == "TRADE_SIGNAL") return MessageType::TRADE_SIGNAL;
        if (messageType == "POSITION_UPDATE") return MessageType::POSITION_UPDATE;
        if (messageType == "PERFORMANCE_UPDATE") return MessageType::PERFORMANCE_UPDATE;
        if (messageType == "SYSTEM_STATUS") return MessageType::SYSTEM_STATUS;
        if (messageType == "ERROR_MESSAGE") return MessageType::ERROR_MESSAGE;
        if (messageType == "HEARTBEAT") return MessageType::HEARTBEAT;
        
        return MessageType::UNKNOWN;
    } catch (const std::exception& e) {
        return MessageType::UNKNOWN;
    }
}

bool SignalParser::isValidMessage(const std::string& jsonStr) {
    try {
        auto j = SimpleJsonParser::parse(jsonStr);
        
        // Check required fields
        if (!j.contains("message_id") || !j.contains("timestamp") || !j.contains("message_type")) {
            return false;
        }
        
        return true;
    } catch (const std::exception& e) {
        return false;
    }
}
