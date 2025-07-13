#include "signal_watcher.h"
#include <iostream>
#include <chrono>
#include <thread>
#include <cstring>

SignalWatcher::SignalWatcher(const std::string& host, int port) 
    : host_(host), port_(port), context_(nullptr), socket_(nullptr), isRunning_(false) {
    
    // Initialize ZMQ context
    context_ = zmq_ctx_new();
    if (!context_) {
        throw std::runtime_error("Failed to create ZMQ context");
    }
    
    // Create socket
    socket_ = zmq_socket(context_, ZMQ_SUB);
    if (!socket_) {
        zmq_ctx_destroy(context_);
        throw std::runtime_error("Failed to create ZMQ socket");
    }
    
    std::string connectionString = "tcp://" + host + ":" + std::to_string(port);
    int rc = zmq_connect(socket_, connectionString.c_str());
    if (rc != 0) {
        zmq_close(socket_);
        zmq_ctx_destroy(context_);
        throw std::runtime_error("Failed to connect to " + connectionString);
    }
    
    // Subscribe to all topics
    rc = zmq_setsockopt(socket_, ZMQ_SUBSCRIBE, "", 0);
    if (rc != 0) {
        zmq_close(socket_);
        zmq_ctx_destroy(context_);
        throw std::runtime_error("Failed to set subscribe option");
    }
    
    // Set receive timeout
    int timeout = 1000; // 1 second
    rc = zmq_setsockopt(socket_, ZMQ_RCVTIMEO, &timeout, sizeof(timeout));
    if (rc != 0) {
        zmq_close(socket_);
        zmq_ctx_destroy(context_);
        throw std::runtime_error("Failed to set receive timeout");
    }
}

SignalWatcher::~SignalWatcher() {
    stop();
    if (socket_) {
        zmq_close(socket_);
    }
    if (context_) {
        zmq_ctx_destroy(context_);
    }
}

void SignalWatcher::start() {
    if (isRunning_) return;
    
    isRunning_ = true;
    receiveThread_ = std::thread(&SignalWatcher::receiveLoop, this);
    std::cout << "Signal watcher started on " << host_ << ":" << port_ << std::endl;
}

void SignalWatcher::stop() {
    if (!isRunning_) return;
    
    isRunning_ = false;
    if (receiveThread_.joinable()) {
        receiveThread_.join();
    }
    std::cout << "Signal watcher stopped" << std::endl;
}

void SignalWatcher::receiveLoop() {
    char topicBuffer[256];
    char messageBuffer[4096];
    
    while (isRunning_) {
        try {
            // Receive topic
            int topicSize = zmq_recv(socket_, topicBuffer, sizeof(topicBuffer) - 1, ZMQ_DONTWAIT);
            if (topicSize == -1) {
                if (zmq_errno() == EAGAIN) {
                    // Timeout, continue
                    std::this_thread::sleep_for(std::chrono::milliseconds(10));
                    continue;
                }
                std::cerr << "ZMQ error receiving topic: " << zmq_strerror(zmq_errno()) << std::endl;
                continue;
            }
            topicBuffer[topicSize] = '\0';
            std::string topic(topicBuffer);
            
            // Receive message
            int messageSize = zmq_recv(socket_, messageBuffer, sizeof(messageBuffer) - 1, ZMQ_DONTWAIT);
            if (messageSize == -1) {
                if (zmq_errno() == EAGAIN) {
                    // Timeout, continue
                    continue;
                }
                std::cerr << "ZMQ error receiving message: " << zmq_strerror(zmq_errno()) << std::endl;
                continue;
            }
            messageBuffer[messageSize] = '\0';
            std::string message(messageBuffer);
            
            // Process message
            processMessage(topic, message);
            
        } catch (const std::exception& e) {
            std::cerr << "Error in receive loop: " << e.what() << std::endl;
        }
    }
}

void SignalWatcher::processMessage(const std::string& topic, const std::string& message) {
    try {
        SignalParser parser;
        
        if (!parser.isValidMessage(message)) {
            std::cerr << "Invalid message received: " << message << std::endl;
            return;
        }
        
        MessageType messageType = parser.getMessageType(message);
        
        switch (messageType) {
            case MessageType::TRADE_SIGNAL:
                handleTradeSignal(parser.parseTradeSignal(message));
                break;
                
            case MessageType::POSITION_UPDATE:
                handlePositionUpdate(parser.parsePositionUpdate(message));
                break;
                
            case MessageType::PERFORMANCE_UPDATE:
                handlePerformanceUpdate(parser.parsePerformanceUpdate(message));
                break;
                
            case MessageType::SYSTEM_STATUS:
                handleSystemStatus(parser.parseSystemStatus(message));
                break;
                
            case MessageType::ERROR_MESSAGE:
                handleErrorMessage(parser.parseErrorMessage(message));
                break;
                
            case MessageType::HEARTBEAT:
                handleHeartbeat(message);
                break;
                
            default:
                std::cout << "Unknown message type received: " << topic << std::endl;
                break;
        }
        
    } catch (const std::exception& e) {
        std::cerr << "Error processing message: " << e.what() << std::endl;
    }
}

void SignalWatcher::handleTradeSignal(const TradeSignal& signal) {
    std::cout << "Received trade signal:" << std::endl;
    std::cout << "  Pair: " << signal.pairName << std::endl;
    std::cout << "  Signal: " << signal.signalType << std::endl;
    std::cout << "  Z-Score: " << signal.zScore << std::endl;
    std::cout << "  Hedge Ratio: " << signal.hedgeRatio << std::endl;
    std::cout << "  Shares A: " << signal.sharesA << std::endl;
    std::cout << "  Shares B: " << signal.sharesB << std::endl;
    std::cout << "  Confidence: " << signal.confidence << std::endl;
    
    // Notify order manager
    if (orderManagerCallback_) {
        orderManagerCallback_(signal);
    }
}

void SignalWatcher::handlePositionUpdate(const PositionUpdate& update) {
    std::cout << "Received position update:" << std::endl;
    std::cout << "  Pair: " << update.pairName << std::endl;
    std::cout << "  Position: " << update.currentPosition << std::endl;
    std::cout << "  Shares A: " << update.sharesA << std::endl;
    std::cout << "  Shares B: " << update.sharesB << std::endl;
    std::cout << "  Market Value: $" << update.marketValue << std::endl;
    std::cout << "  Unrealized P&L: $" << update.unrealizedPnl << std::endl;
}

void SignalWatcher::handlePerformanceUpdate(const PerformanceUpdate& update) {
    std::cout << "Received performance update:" << std::endl;
    std::cout << "  Total P&L: $" << update.totalPnl << std::endl;
    std::cout << "  Daily P&L: $" << update.dailyPnl << std::endl;
    std::cout << "  Total Return: " << (update.totalReturn * 100) << "%" << std::endl;
    std::cout << "  Sharpe Ratio: " << update.sharpeRatio << std::endl;
    std::cout << "  Max Drawdown: " << (update.maxDrawdown * 100) << "%" << std::endl;
    std::cout << "  Active Positions: " << update.totalPositions << std::endl;
    std::cout << "  Cash Balance: $" << update.cashBalance << std::endl;
}

void SignalWatcher::handleSystemStatus(const SystemStatus& status) {
    std::cout << "Received system status:" << std::endl;
    std::cout << "  Component: " << status.component << std::endl;
    std::cout << "  Status: " << status.status << std::endl;
    std::cout << "  Uptime: " << status.uptimeSeconds << "s" << std::endl;
    std::cout << "  CPU: " << status.cpuUsagePercent << "%" << std::endl;
    std::cout << "  Memory: " << status.memoryUsageMb << "MB" << std::endl;
    std::cout << "  Message: " << status.message << std::endl;
}

void SignalWatcher::handleErrorMessage(const ErrorMessage& error) {
    std::cerr << "Received error message:" << std::endl;
    std::cerr << "  Type: " << error.errorType << std::endl;
    std::cerr << "  Code: " << error.errorCode << std::endl;
    std::cerr << "  Severity: " << error.severity << std::endl;
    std::cerr << "  Component: " << error.component << std::endl;
    std::cerr << "  Message: " << error.errorMessage << std::endl;
    
    if (!error.pairName.empty()) {
        std::cerr << "  Pair: " << error.pairName << std::endl;
    }
}

void SignalWatcher::handleHeartbeat(const std::string& message) {
    // Just log heartbeat for now
    std::cout << "Received heartbeat from Python data engine" << std::endl;
}

void SignalWatcher::setOrderManagerCallback(OrderManagerCallback callback) {
    orderManagerCallback_ = callback;
}

bool SignalWatcher::isConnected() const {
    return isRunning_;
}

std::string SignalWatcher::getConnectionInfo() const {
    return "tcp://" + host_ + ":" + std::to_string(port_);
}
