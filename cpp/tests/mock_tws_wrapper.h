#pragma once

#include <string>
#include <map>
#include <vector>
#include <functional>

// Mock contract and order structures
struct MockContract {
    std::string symbol;
    std::string secType;
    std::string exchange;
    std::string currency;
};

struct MockOrder {
    std::string action;
    int totalQuantity;
    std::string orderType;
    double lmtPrice;
    double auxPrice;
};

struct OrderInfo {
    MockContract contract;
    MockOrder order;
    std::string status;
};

class MockTWSWrapper {
public:
    MockTWSWrapper() : isConnected_(false), nextOrderId_(1) {}
    
    // Connection methods
    bool eConnect(const std::string& host, int port, int clientId) {
        isConnected_ = true;
        std::cout << "Mock TWS: Connected to " << host << ":" << port << std::endl;
        return true;
    }
    
    bool isConnected() const {
        return isConnected_;
    }
    
    void eDisconnect() {
        isConnected_ = false;
        std::cout << "Mock TWS: Disconnected" << std::endl;
    }
    
    // Order methods
    int placeOrder(int orderId, const MockContract& contract, const MockOrder& order) {
        if (!isConnected_) {
            std::cerr << "Mock TWS: Not connected" << std::endl;
            return -1;
        }
        
        std::cout << "Mock TWS: Placed order " << orderId 
                  << " - " << order.action << " " << order.totalQuantity 
                  << " " << contract.symbol << " @ " << order.lmtPrice << std::endl;
        
        // Store order for tracking
        orders_[orderId] = {contract, order, "Submitted"};
        
        // Simulate order status updates
        simulateOrderStatus(orderId, "Submitted");
        
        return orderId;
    }
    
    void cancelOrder(int orderId) {
        if (orders_.find(orderId) != orders_.end()) {
            orders_[orderId].status = "Cancelled";
            std::cout << "Mock TWS: Cancelled order " << orderId << std::endl;
            simulateOrderStatus(orderId, "Cancelled");
        }
    }
    
    // Mock order status simulation
    void simulateOrderStatus(int orderId, const std::string& status) {
        if (orders_.find(orderId) == orders_.end()) return;
        
        auto& orderInfo = orders_[orderId];
        orderInfo.status = status;
        
        // Simulate fill for market orders
        if (status == "Submitted" && orderInfo.order.orderType == "MKT") {
            // Simulate immediate fill
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            orderInfo.status = "Filled";
            simulateOrderStatus(orderId, "Filled");
        }
    }
    
    // Get order status
    std::string getOrderStatus(int orderId) const {
        auto it = orders_.find(orderId);
        return (it != orders_.end()) ? it->second.status : "Unknown";
    }
    
    // Get all orders
    const std::map<int, OrderInfo>& getOrders() const {
        return orders_;
    }
    
    // Set callback for order status updates
    void setOrderStatusCallback(std::function<void(int, const std::string&, int, int, double)> callback) {
        orderStatusCallback_ = callback;
    }
    
    // Set callback for errors
    void setErrorCallback(std::function<void(int, int, const std::string&)> callback) {
        errorCallback_ = callback;
    }
    
    // Simulate market data
    void simulateMarketData(const std::string& symbol, double price) {
        marketPrices_[symbol] = price;
        std::cout << "Mock TWS: Market data - " << symbol << " @ $" << price << std::endl;
    }
    
    // Get market price
    double getMarketPrice(const std::string& symbol) const {
        auto it = marketPrices_.find(symbol);
        return (it != marketPrices_.end()) ? it->second : 0.0;
    }
    
    // Simulate connection issues
    void simulateConnectionLoss() {
        isConnected_ = false;
        std::cout << "Mock TWS: Connection lost" << std::endl;
    }
    
    void simulateReconnection() {
        isConnected_ = true;
        std::cout << "Mock TWS: Reconnected" << std::endl;
    }
    
private:
    bool isConnected_;
    int nextOrderId_;
    std::map<int, OrderInfo> orders_;
    std::map<std::string, double> marketPrices_;
    std::function<void(int, const std::string&, int, int, double)> orderStatusCallback_;
    std::function<void(int, int, const std::string&)> errorCallback_;
}; 