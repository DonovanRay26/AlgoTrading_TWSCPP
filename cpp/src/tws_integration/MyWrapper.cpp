#include "MyWrapper.h"
#include "../include/order_manager.h"

void MyWrapper::error(int id, int errorCode, const std::string& errorString, const std::string& advancedOrderRejectJson) {
    std::cerr << "Error " << errorCode << ": " << errorString << std::endl;
    
    // Forward to order manager if available
    if (orderManager_) {
        orderManager_->onError(id, errorCode, errorString, advancedOrderRejectJson);
    }
}

void MyWrapper::orderStatus(OrderId orderId, const std::string& status, Decimal filled,
                          Decimal remaining, double avgFillPrice, int permId, int parentId,
                          double lastFillPrice, int clientId, const std::string& whyHeld, double mktCapPrice) {
    
    // Forward to order manager if available
    if (orderManager_) {
        orderManager_->onOrderStatus(orderId, status, filled, remaining, avgFillPrice, 
                                   permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice);
    }
}

void MyWrapper::tickPrice(TickerId tickerId, TickType field, double price, const TickAttrib& attrib) {
    // Handle tick price updates
    std::cout << "Tick Price - ID: " << tickerId << ", Field: " << field << ", Price: " << price << std::endl;
} 