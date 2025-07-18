// OrderUtils.h
#pragma once

#include "Contract.h"
#include "Order.h"
#include <string>

Contract createStockContract(const std::string& symbol);
Order createLimitOrder(const std::string& action, int quantity, double price);  // Specify a limit to buy/sell at
Order createMarketOrder(const std::string& action, int quantity);  // Non-specific order