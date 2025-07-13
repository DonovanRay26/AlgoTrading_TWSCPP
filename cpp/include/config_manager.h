#pragma once

#include <string>
#include <map>
#include <memory>

class ConfigManager {
public:
    static ConfigManager& getInstance();
    
    // Risk management settings
    double getMaxPositionSize() const { return maxPositionSize_; }
    double getMaxDailyLoss() const { return maxDailyLoss_; }
    double getMaxTotalExposure() const { return maxTotalExposure_; }
    double getMinConfidence() const { return minConfidence_; }
    double getMaxZScore() const { return maxZScore_; }
    
    // Network settings
    std::string getZMQHost() const { return zmqHost_; }
    int getZMQPort() const { return zmqPort_; }
    
    // TWS settings
    std::string getTWSHost() const { return twsHost_; }
    int getTWSPort() const { return twsPort_; }
    int getTWSClientId() const { return twsClientId_; }
    
    // Load configuration from file
    bool loadFromFile(const std::string& filename);
    
    // Set values programmatically
    void setRiskLimits(double maxPositionSize, double maxDailyLoss, 
                      double maxTotalExposure, double minConfidence, double maxZScore);
    void setNetworkSettings(const std::string& host, int port);
    void setTWSSettings(const std::string& host, int port, int clientId);

private:
    ConfigManager() = default;
    ConfigManager(const ConfigManager&) = delete;
    ConfigManager& operator=(const ConfigManager&) = delete;
    
    // Risk management defaults
    double maxPositionSize_ = 10000;
    double maxDailyLoss_ = 5000.0;
    double maxTotalExposure_ = 100000.0;
    double minConfidence_ = 0.7;
    double maxZScore_ = 3.0;
    
    // Network defaults
    std::string zmqHost_ = "localhost";
    int zmqPort_ = 5555;
    
    // TWS defaults
    std::string twsHost_ = "127.0.0.1";
    int twsPort_ = 7497;
    int twsClientId_ = 0;
}; 