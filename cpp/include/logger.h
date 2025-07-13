#pragma once

#include <string>
#include <iostream>
#include <fstream>
#include <memory>
#include <mutex>

enum class LogLevel {
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL
};

class Logger {
public:
    static Logger& getInstance();
    
    void setLogLevel(LogLevel level) { logLevel_ = level; }
    void setLogFile(const std::string& filename);
    
    void debug(const std::string& message);
    void info(const std::string& message);
    void warning(const std::string& message);
    void error(const std::string& message);
    void critical(const std::string& message);
    
    // Convenience methods for trading-specific logging
    void logSignal(const std::string& signalType, const std::string& pairName, double confidence);
    void logOrder(const std::string& action, const std::string& symbol, int quantity, double price);
    void logRiskCheck(const std::string& checkType, bool passed, const std::string& details);
    void logPosition(const std::string& symbol, int quantity, double avgPrice, double unrealizedPnl);

private:
    Logger() = default;
    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;
    
    void log(LogLevel level, const std::string& message);
    std::string getLevelString(LogLevel level) const;
    std::string getTimestamp() const;
    
    LogLevel logLevel_ = LogLevel::INFO;
    std::ofstream logFile_;
    std::mutex logMutex_;
    bool useFile_ = false;
};

// Convenience macros
#define LOG_DEBUG(msg) Logger::getInstance().debug(msg)
#define LOG_INFO(msg) Logger::getInstance().info(msg)
#define LOG_WARNING(msg) Logger::getInstance().warning(msg)
#define LOG_ERROR(msg) Logger::getInstance().error(msg)
#define LOG_CRITICAL(msg) Logger::getInstance().critical(msg)
