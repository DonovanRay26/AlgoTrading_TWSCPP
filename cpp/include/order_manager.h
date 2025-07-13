#pragma once

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <functional>
#include "signal_parser.h"
#include "../src/tws_integration/MyWrapper.h"
#include "../src/tws_integration/OrderUtils.h"

// Forward declarations
class PositionTracker;
class RiskChecker;

struct OrderRequest {
    std::string symbol;
    std::string action;  // "BUY" or "SELL"
    int quantity;
    std::string orderType;  // "MKT" or "LMT"
    double limitPrice;  // Only used for limit orders
    int orderId;
};

struct PairPositions {
    std::string pairName;
    int sharesA;
    int sharesB;
    double avgPriceA;
    double avgPriceB;
    double marketValue;
    double unrealizedPnl;
};

class OrderManager {
public:
    explicit OrderManager(MyWrapper& wrapper);
    ~OrderManager();
    
    // Start/stop order manager
    void start();
    void stop();
    
    // Handle trade signals from Python
    void handleTradeSignal(const TradeSignal& signal);
    
    // Order status callbacks (called by TWS wrapper)
    void onOrderStatus(int orderId, const std::string& status, int filled, 
                      int remaining, double avgFillPrice, int permId, 
                      int parentId, double lastFillPrice, int clientId, 
                      const std::string& whyHeld, double mktCapPrice);
    
    void onError(int id, int errorCode, const std::string& errorString, 
                const std::string& advancedOrderRejectJson);
    
    // Status
    bool isRunning() const;
    std::map<std::string, double> getCurrentPositions() const;
    
private:
    // TWS wrapper reference
    MyWrapper& wrapper_;
    
    // Components
    std::unique_ptr<PositionTracker> positionTracker_;
    std::unique_ptr<RiskChecker> riskChecker_;
    
    // Order tracking
    std::map<int, OrderRequest> pendingOrders_;
    int nextOrderId_;
    bool isRunning_;
    
    // Internal methods
    bool validateSignal(const TradeSignal& signal);
    void executeSignal(const TradeSignal& signal);
    
    std::vector<OrderRequest> createLongSpreadOrders(const TradeSignal& signal, 
                                                    const PairPositions& currentPositions);
    std::vector<OrderRequest> createShortSpreadOrders(const TradeSignal& signal, 
                                                      const PairPositions& currentPositions);
    std::vector<OrderRequest> createExitOrders(const TradeSignal& signal, 
                                              const PairPositions& currentPositions);
    
    bool placeOrder(const OrderRequest& orderReq);
    void cancelAllOrders();
    int getNextOrderId();
};
