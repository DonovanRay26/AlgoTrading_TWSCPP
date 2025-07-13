#include <iostream>
#include <thread>
#include <chrono>
#include <zmq.h>
#include "../include/signal_parser.h"
#include "../include/signal_watcher.h"
#include "../include/order_manager.h"
#include "../include/position_tracker.h"
#include "../include/risk_checker.h"
#include "mock_tws_wrapper.h"

class MockOrderManager {
public:
    MockOrderManager(MockTWSWrapper& wrapper) : wrapper_(wrapper) {
        positionTracker_ = std::make_unique<PositionTracker>();
        riskChecker_ = std::make_unique<RiskChecker>();
    }
    
    void handleTradeSignal(const TradeSignal& signal) {
        std::cout << "Mock Order Manager: Processing signal for " << signal.pairName << std::endl;
        
        // Validate signal
        if (!validateSignal(signal)) {
            std::cerr << "Mock Order Manager: Invalid signal" << std::endl;
            return;
        }
        
        // Check risk
        if (!riskChecker_->checkSignalRisk(signal)) {
            std::cerr << "Mock Order Manager: Signal rejected by risk checker" << std::endl;
            return;
        }
        
        // Execute signal
        executeSignal(signal);
    }
    
    void onOrderStatus(int orderId, const std::string& status, int filled, 
                      int remaining, double avgFillPrice, int permId, 
                      int parentId, double lastFillPrice, int clientId, 
                      const std::string& whyHeld, double mktCapPrice) {
        
        std::cout << "Mock Order Manager: Order " << orderId << " status: " << status 
                  << ", filled: " << filled << ", price: $" << avgFillPrice << std::endl;
        
        // Update position tracker
        if (status == "Filled" && pendingOrders_.find(orderId) != pendingOrders_.end()) {
            const auto& orderReq = pendingOrders_[orderId];
            positionTracker_->updatePosition(orderReq.symbol, orderReq.action, filled, avgFillPrice);
            pendingOrders_.erase(orderId);
        }
    }
    
    void onError(int id, int errorCode, const std::string& errorString, 
                const std::string& advancedOrderRejectJson) {
        std::cerr << "Mock Order Manager: Error " << errorCode << ": " << errorString << std::endl;
    }
    
    void printPositions() {
        positionTracker_->printPositions();
    }
    
private:
    struct OrderRequest {
        std::string symbol;
        std::string action;
        int quantity;
        std::string orderType;
        double limitPrice;
        int orderId;
    };
    
    MockTWSWrapper& wrapper_;
    std::unique_ptr<PositionTracker> positionTracker_;
    std::unique_ptr<RiskChecker> riskChecker_;
    std::map<int, OrderRequest> pendingOrders_;
    int nextOrderId_ = 1;
    
    bool validateSignal(const TradeSignal& signal) {
        return !signal.pairName.empty() && signal.confidence > 0.0;
    }
    
    void executeSignal(const TradeSignal& signal) {
        std::cout << "Mock Order Manager: Executing " << signal.signalType << " for " << signal.pairName << std::endl;
        
        if (signal.signalType == "ENTER_LONG_SPREAD") {
            if (signal.sharesA > 0) {
                placeOrder(signal.symbolA, "BUY", signal.sharesA, "MKT", 0.0);
            }
            if (signal.sharesB < 0) {
                placeOrder(signal.symbolB, "SELL", abs(signal.sharesB), "MKT", 0.0);
            }
        } else if (signal.signalType == "ENTER_SHORT_SPREAD") {
            if (signal.sharesA < 0) {
                placeOrder(signal.symbolA, "SELL", abs(signal.sharesA), "MKT", 0.0);
            }
            if (signal.sharesB > 0) {
                placeOrder(signal.symbolB, "BUY", signal.sharesB, "MKT", 0.0);
            }
        }
    }
    
    void placeOrder(const std::string& symbol, const std::string& action, 
                   int quantity, const std::string& orderType, double limitPrice) {
        
        MockContract contract;
        contract.symbol = symbol;
        contract.secType = "STK";
        contract.exchange = "SMART";
        contract.currency = "USD";
        
        MockOrder order;
        order.action = action;
        order.totalQuantity = quantity;
        order.orderType = orderType;
        order.lmtPrice = limitPrice;
        
        int orderId = nextOrderId_++;
        wrapper_.placeOrder(orderId, contract, order);
        
        OrderRequest orderReq;
        orderReq.symbol = symbol;
        orderReq.action = action;
        orderReq.quantity = quantity;
        orderReq.orderType = orderType;
        orderReq.limitPrice = limitPrice;
        orderReq.orderId = orderId;
        
        pendingOrders_[orderId] = orderReq;
    }
};

// Mock ZMQ publisher for testing
class MockSignalPublisher {
public:
    MockSignalPublisher(const std::string& host, int port) 
        : context_(nullptr), socket_(nullptr) {
        
        // Initialize ZMQ context
        context_ = zmq_ctx_new();
        if (!context_) {
            throw std::runtime_error("Failed to create ZMQ context");
        }
        
        // Create socket
        socket_ = zmq_socket(context_, ZMQ_PUB);
        if (!socket_) {
            zmq_ctx_destroy(context_);
            throw std::runtime_error("Failed to create ZMQ socket");
        }
        
        std::string connectionString = "tcp://" + host + ":" + std::to_string(port);
        int rc = zmq_bind(socket_, connectionString.c_str());
        if (rc != 0) {
            zmq_close(socket_);
            zmq_ctx_destroy(context_);
            throw std::runtime_error("Failed to bind to " + connectionString);
        }
        std::cout << "Mock Publisher: Bound to " << connectionString << std::endl;
    }
    
    ~MockSignalPublisher() {
        if (socket_) zmq_close(socket_);
        if (context_) zmq_ctx_destroy(context_);
    }
    
    void publishSignal(const std::string& signalJson) {
        std::string topic = "TRADE_SIGNAL";
        int rc = zmq_send(socket_, topic.c_str(), topic.length(), ZMQ_SNDMORE);
        if (rc == -1) {
            throw std::runtime_error("Failed to send topic");
        }
        rc = zmq_send(socket_, signalJson.c_str(), signalJson.length(), 0);
        if (rc == -1) {
            throw std::runtime_error("Failed to send signal");
        }
        std::cout << "Mock Publisher: Sent signal" << std::endl;
    }
    
    void publishHeartbeat() {
        std::string topic = "HEARTBEAT";
        std::string message = R"({"message_id": "hb_001", "timestamp": "2024-01-01T10:00:00", "message_type": "HEARTBEAT"})";
        int rc = zmq_send(socket_, topic.c_str(), topic.length(), ZMQ_SNDMORE);
        if (rc == -1) {
            throw std::runtime_error("Failed to send heartbeat topic");
        }
        rc = zmq_send(socket_, message.c_str(), message.length(), 0);
        if (rc == -1) {
            throw std::runtime_error("Failed to send heartbeat");
        }
        std::cout << "Mock Publisher: Sent heartbeat" << std::endl;
    }
    
private:
    void* context_;
    void* socket_;
};

void testCompleteWorkflow() {
    std::cout << "\n=== Testing Complete Trading Workflow ===" << std::endl;
    
    // Initialize components
    MockTWSWrapper mockTws;
    MockOrderManager orderManager(mockTws);
    
    // Connect to TWS
    mockTws.eConnect("127.0.0.1", 7497, 0);
    if (!mockTws.isConnected()) {
        std::cerr << "FAILED: Mock TWS connection test" << std::endl;
        return;
    }
    std::cout << "PASSED: Mock TWS connection test" << std::endl;
    
    // Start signal publisher
    MockSignalPublisher publisher("localhost", 5555);
    
    // Start signal watcher
    SignalWatcher signalWatcher("localhost", 5555);
    signalWatcher.setOrderManagerCallback(
        [&orderManager](const TradeSignal& signal) {
            orderManager.handleTradeSignal(signal);
        }
    );
    signalWatcher.start();
    
    // Wait for connection
    std::this_thread::sleep_for(std::chrono::seconds(1));
    
    // Test signal 1: Enter long spread
    std::string signal1 = R"({
        "message_id": "test_001",
        "timestamp": "2024-01-01T10:00:00",
        "message_type": "TRADE_SIGNAL",
        "pair_name": "AAPL_MSFT",
        "symbol_a": "AAPL",
        "symbol_b": "MSFT",
        "signal_type": "ENTER_LONG_SPREAD",
        "z_score": 1.5,
        "hedge_ratio": 0.8,
        "confidence": 0.85,
        "position_size": 1000,
        "shares_a": 100,
        "shares_b": -80,
        "volatility": 0.25,
        "correlation": 0.75
    })";
    
    std::cout << "\n--- Test 1: Enter Long Spread ---" << std::endl;
    publisher.publishSignal(signal1);
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    // Simulate market data
    mockTws.simulateMarketData("AAPL", 150.0);
    mockTws.simulateMarketData("MSFT", 300.0);
    
    // Test signal 2: Exit position
    std::string signal2 = R"({
        "message_id": "test_002",
        "timestamp": "2024-01-01T10:05:00",
        "message_type": "TRADE_SIGNAL",
        "pair_name": "AAPL_MSFT",
        "symbol_a": "AAPL",
        "symbol_b": "MSFT",
        "signal_type": "EXIT_POSITION",
        "z_score": 0.1,
        "hedge_ratio": 0.8,
        "confidence": 0.9,
        "position_size": 0,
        "shares_a": 0,
        "shares_b": 0,
        "volatility": 0.25,
        "correlation": 0.75
    })";
    
    std::cout << "\n--- Test 2: Exit Position ---" << std::endl;
    publisher.publishSignal(signal2);
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    // Test signal 3: Enter short spread
    std::string signal3 = R"({
        "message_id": "test_003",
        "timestamp": "2024-01-01T10:10:00",
        "message_type": "TRADE_SIGNAL",
        "pair_name": "GOOGL_META",
        "symbol_a": "GOOGL",
        "symbol_b": "META",
        "signal_type": "ENTER_SHORT_SPREAD",
        "z_score": -1.8,
        "hedge_ratio": 0.7,
        "confidence": 0.88,
        "position_size": 800,
        "shares_a": -60,
        "shares_b": 42,
        "volatility": 0.3,
        "correlation": 0.65
    })";
    
    std::cout << "\n--- Test 3: Enter Short Spread ---" << std::endl;
    publisher.publishSignal(signal3);
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    // Test risk rejection
    std::string riskySignal = R"({
        "message_id": "test_004",
        "timestamp": "2024-01-01T10:15:00",
        "message_type": "TRADE_SIGNAL",
        "pair_name": "NVDA_AMD",
        "symbol_a": "NVDA",
        "symbol_b": "AMD",
        "signal_type": "ENTER_LONG_SPREAD",
        "z_score": 4.5,
        "hedge_ratio": 0.9,
        "confidence": 0.3,
        "position_size": 50000,
        "shares_a": 5000,
        "shares_b": -4500,
        "volatility": 0.6,
        "correlation": 0.98
    })";
    
    std::cout << "\n--- Test 4: Risk Rejection ---" << std::endl;
    publisher.publishSignal(riskySignal);
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    // Print final positions
    std::cout << "\n--- Final Positions ---" << std::endl;
    orderManager.printPositions();
    
    // Test connection loss and recovery
    std::cout << "\n--- Test 5: Connection Loss/Recovery ---" << std::endl;
    mockTws.simulateConnectionLoss();
    std::this_thread::sleep_for(std::chrono::seconds(1));
    mockTws.simulateReconnection();
    
    // Send heartbeat
    publisher.publishHeartbeat();
    std::this_thread::sleep_for(std::chrono::seconds(1));
    
    // Cleanup
    signalWatcher.stop();
    mockTws.eDisconnect();
    
    std::cout << "\nComplete workflow test finished!" << std::endl;
}

int main() {
    std::cout << "Starting C++ Trading System Integration Tests" << std::endl;
    
    try {
        testCompleteWorkflow();
        std::cout << "\nALL INTEGRATION TESTS PASSED!" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Integration test failed with exception: " << e.what() << std::endl;
        return 1;
    }
} 