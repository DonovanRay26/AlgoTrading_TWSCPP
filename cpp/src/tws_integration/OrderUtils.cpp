// OrderUtils.cpp
#include "OrderUtils.h"

Contract createStockContract(const std::string& symbol) {
    Contract contract;
    contract.symbol = symbol;
    contract.secType = "STK";
    contract.exchange = "SMART";
    contract.currency = "USD";
    return contract;
}

Order createLimitOrder(const std::string& action, int quantity, double price) {
    Order order;
    order.action = action;  // "BUY" or "SELL"
    order.orderType = "LMT";  // Limit order
    order.totalQuantity = quantity;
    order.lmtPrice = price;
    order.transmit = true;
    return order;
}

Order createMarketOrder(const std::string& action, int quantity) {
    Order order;
    order.action = action;  // "BUY" or "SELL"
    order.orderType = "MKT";  // Market order
    order.totalQuantity = quantity;
    order.transmit = true;
    return order;
}