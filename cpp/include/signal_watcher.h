#pragma once

#include <string>
#include <thread>
#include <functional>
#include <zmq.h>
#include "signal_parser.h"

// Forward declaration
class OrderManager;

// Callback type for order manager
using OrderManagerCallback = std::function<void(const TradeSignal&)>;

class SignalWatcher {
public:
    SignalWatcher(const std::string& host, int port);
    ~SignalWatcher();
    
    // Start/stop the signal watcher
    void start();
    void stop();
    
    // Set callback for order manager
    void setOrderManagerCallback(OrderManagerCallback callback);
    
    // Status
    bool isConnected() const;
    std::string getConnectionInfo() const;
    
private:
    // ZMQ connection
    std::string host_;
    int port_;
    void* context_;
    void* socket_;
    
    // Threading
    std::thread receiveThread_;
    bool isRunning_;
    
    // Callback
    OrderManagerCallback orderManagerCallback_;
    
    // Internal methods
    void receiveLoop();
    void processMessage(const std::string& topic, const std::string& message);
    
    // Message handlers
    void handleTradeSignal(const TradeSignal& signal);
    void handlePositionUpdate(const PositionUpdate& update);
    void handlePerformanceUpdate(const PerformanceUpdate& update);
    void handleSystemStatus(const SystemStatus& status);
    void handleErrorMessage(const ErrorMessage& error);
    void handleHeartbeat(const std::string& message);
};
