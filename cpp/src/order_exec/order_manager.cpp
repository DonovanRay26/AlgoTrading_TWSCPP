#include "order_manager.h"
#include "position_tracker.h"
#include "risk_checker.h"
#include <iostream>
#include <chrono>
#include <thread>

OrderManager::OrderManager(MyWrapper& wrapper) 
    : wrapper_(wrapper), nextOrderId_(1), isRunning_(false) {
    
    // Initialize position tracker
    positionTracker_ = std::make_unique<PositionTracker>();
    
    // Initialize risk checker
    riskChecker_ = std::make_unique<RiskChecker>();
    
    std::cout << "Order manager initialized" << std::endl;
}

OrderManager::~OrderManager() {
    stop();
}

void OrderManager::start() {
    if (isRunning_) return;
    
    isRunning_ = true;
    std::cout << "Order manager started" << std::endl;
}

void OrderManager::stop() {
    if (!isRunning_) return;
    
    isRunning_ = false;
    
    // Cancel all pending orders
    cancelAllOrders();
    
    std::cout << "Order manager stopped" << std::endl;
}

void OrderManager::handleTradeSignal(const TradeSignal& signal) {
    if (!isRunning_) {
        std::cout << "Order manager not running, ignoring signal" << std::endl;
        return;
    }
    
    std::cout << "Processing trade signal for " << signal.pairName << std::endl;
    
    try {
        // Validate signal
        if (!validateSignal(signal)) {
            std::cerr << "Invalid trade signal received" << std::endl;
            return;
        }
        
        // Check risk limits
        if (!riskChecker_->checkSignalRisk(signal)) {
            std::cerr << "Signal rejected by risk checker" << std::endl;
            return;
        }
        
        // Execute the signal
        executeSignal(signal);
        
    } catch (const std::exception& e) {
        std::cerr << "Error processing trade signal: " << e.what() << std::endl;
    }
}

bool OrderManager::validateSignal(const TradeSignal& signal) {
    // Basic validation
    if (signal.pairName.empty() || signal.symbolA.empty() || signal.symbolB.empty()) {
        return false;
    }
    
    if (signal.sharesA == 0 && signal.sharesB == 0) {
        return false;
    }
    
    if (signal.confidence < 0.0 || signal.confidence > 1.0) {
        return false;
    }
    
    return true;
}

void OrderManager::executeSignal(const TradeSignal& signal) {
    std::cout << "Executing signal: " << signal.signalType << " for " << signal.pairName << std::endl;
    
    // Get current positions for this pair
    auto currentPositions = positionTracker_->getPairPositions(signal.pairName);
    
    // Determine what orders to place
    std::vector<OrderRequest> orders;
    
    if (signal.signalType == "ENTER_LONG_SPREAD") {
        orders = createLongSpreadOrders(signal, currentPositions);
    } else if (signal.signalType == "ENTER_SHORT_SPREAD") {
        orders = createShortSpreadOrders(signal, currentPositions);
    } else if (signal.signalType == "EXIT_POSITION") {
        orders = createExitOrders(signal, currentPositions);
    } else {
        std::cerr << "Unknown signal type: " << signal.signalType << std::endl;
        return;
    }
    
    // Place orders
    for (const auto& orderReq : orders) {
        placeOrder(orderReq);
    }
    
    // Update position tracking
    positionTracker_->updatePositions(signal.pairName, orders);
}

std::vector<OrderRequest> OrderManager::createLongSpreadOrders(const TradeSignal& signal, 
                                                             const PairPositions& currentPositions) {
    std::vector<OrderRequest> orders;
    
    // Long spread: Long A, Short B
    if (signal.sharesA > 0) {
        OrderRequest buyOrder;
        buyOrder.symbol = signal.symbolA;
        buyOrder.action = "BUY";
        buyOrder.quantity = signal.sharesA;
        buyOrder.orderType = "MKT";  // Market order for speed
        buyOrder.orderId = getNextOrderId();
        orders.push_back(buyOrder);
    }
    
    if (signal.sharesB < 0) {
        OrderRequest sellOrder;
        sellOrder.symbol = signal.symbolB;
        sellOrder.action = "SELL";
        sellOrder.quantity = abs(signal.sharesB);
        sellOrder.orderType = "MKT";  // Market order for speed
        sellOrder.orderId = getNextOrderId();
        orders.push_back(sellOrder);
    }
    
    return orders;
}

std::vector<OrderRequest> OrderManager::createShortSpreadOrders(const TradeSignal& signal, 
                                                               const PairPositions& currentPositions) {
    std::vector<OrderRequest> orders;
    
    // Short spread: Short A, Long B
    if (signal.sharesA < 0) {
        OrderRequest sellOrder;
        sellOrder.symbol = signal.symbolA;
        sellOrder.action = "SELL";
        sellOrder.quantity = abs(signal.sharesA);
        sellOrder.orderType = "MKT";  // Market order for speed
        sellOrder.orderId = getNextOrderId();
        orders.push_back(sellOrder);
    }
    
    if (signal.sharesB > 0) {
        OrderRequest buyOrder;
        buyOrder.symbol = signal.symbolB;
        buyOrder.action = "BUY";
        buyOrder.quantity = signal.sharesB;
        buyOrder.orderType = "MKT";  // Market order for speed
        buyOrder.orderId = getNextOrderId();
        orders.push_back(buyOrder);
    }
    
    return orders;
}

std::vector<OrderRequest> OrderManager::createExitOrders(const TradeSignal& signal, 
                                                        const PairPositions& currentPositions) {
    std::vector<OrderRequest> orders;
    
    // Exit all positions for this pair
    if (currentPositions.sharesA != 0) {
        OrderRequest exitOrder;
        exitOrder.symbol = signal.symbolA;
        exitOrder.action = (currentPositions.sharesA > 0) ? "SELL" : "BUY";
        exitOrder.quantity = abs(currentPositions.sharesA);
        exitOrder.orderType = "MKT";
        exitOrder.orderId = getNextOrderId();
        orders.push_back(exitOrder);
    }
    
    if (currentPositions.sharesB != 0) {
        OrderRequest exitOrder;
        exitOrder.symbol = signal.symbolB;
        exitOrder.action = (currentPositions.sharesB > 0) ? "SELL" : "BUY";
        exitOrder.quantity = abs(currentPositions.sharesB);
        exitOrder.orderType = "MKT";
        exitOrder.orderId = getNextOrderId();
        orders.push_back(exitOrder);
    }
    
    return orders;
}

bool OrderManager::placeOrder(const OrderRequest& orderReq) {
    try {
        // Create contract
        Contract contract = createStockContract(orderReq.symbol);
        
        // Create order
        Order order;
        if (orderReq.orderType == "MKT") {
            order = createMarketOrder(orderReq.action, orderReq.quantity);
        } else {
            order = createLimitOrder(orderReq.action, orderReq.quantity, orderReq.limitPrice);
        }
        
        // Place order
        wrapper_.client.placeOrder(orderReq.orderId, contract, order);
        
        std::cout << "Placed " << orderReq.action << " order for " << orderReq.quantity 
                  << " shares of " << orderReq.symbol << " (Order ID: " << orderReq.orderId << ")" << std::endl;
        
        // Track the order
        pendingOrders_[orderReq.orderId] = orderReq;
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Error placing order: " << e.what() << std::endl;
        return false;
    }
}

void OrderManager::cancelAllOrders() {
    std::cout << "Clearing pending orders list..." << std::endl;
    
    // Simply clear the pending orders list without attempting to cancel
    // Orders will either fill naturally or be handled by TWS -- note that this approach has been taken due to TWS compatibility issues. 
    pendingOrders_.clear();
}

int OrderManager::getNextOrderId() {
    return nextOrderId_++;
}

void OrderManager::onOrderStatus(int orderId, const std::string& status, int filled, 
                                int remaining, double avgFillPrice, int permId, 
                                int parentId, double lastFillPrice, int clientId, 
                                const std::string& whyHeld, double mktCapPrice) {
    
    std::cout << "Order status update - ID: " << orderId 
              << ", Status: " << status 
              << ", Filled: " << filled 
              << ", Remaining: " << remaining 
              << ", Avg Fill: $" << avgFillPrice << std::endl;
    
    // Update position tracker
    if (pendingOrders_.find(orderId) != pendingOrders_.end()) {
        const auto& orderReq = pendingOrders_[orderId];
        
        if (status == "Filled" || status == "PartiallyFilled") {
            // Update position with filled quantity
            positionTracker_->updatePosition(orderReq.symbol, orderReq.action, filled, avgFillPrice);
            
            // Update risk checker with new metrics
            riskChecker_->updateDailyPnl(positionTracker_->getDailyPnl());
            riskChecker_->updateTotalExposure(positionTracker_->getPositionExposure());
            riskChecker_->updateDrawdown(positionTracker_->getCurrentDrawdown());
            
            // Add PnL history entry
            positionTracker_->addPnLHistory();
            
            // Print updated metrics
            positionTracker_->printPnLSummary();
            riskChecker_->printRiskStatus();
        }
        
        if (status == "Filled" || status == "Cancelled") {
            // Remove from pending orders
            pendingOrders_.erase(orderId);
        }
    }
}

void OrderManager::onError(int id, int errorCode, const std::string& errorString, 
                          const std::string& advancedOrderRejectJson) {
    
    std::cerr << "TWS Error - ID: " << id 
              << ", Code: " << errorCode 
              << ", Message: " << errorString << std::endl;
    
    // Handle specific error codes
    if (errorCode == 202) {  // Order cancelled
        if (pendingOrders_.find(id) != pendingOrders_.end()) {
            pendingOrders_.erase(id);
        }
    }
}

std::map<std::string, double> OrderManager::getCurrentPositions() const {
    return positionTracker_->getAllPositions();
}

bool OrderManager::isRunning() const {
    return isRunning_;
}
