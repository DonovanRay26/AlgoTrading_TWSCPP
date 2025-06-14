#include "MyWrapper.h"
#include "OrderUtils.h"
#include <thread>
#include <chrono>

int main() {
    MyWrapper wrapper;

    if (wrapper.client.eConnect("127.0.0.1", 7497, 0)) {
        std::cout << "eConnect called, waiting for connection..." << std::endl;
    }

    std::this_thread::sleep_for(std::chrono::seconds(1));

    if (wrapper.client.isConnected()) {
        std::cout << "Connected to TWS successfully!" << std::endl;

        // TODO: apply an actual trading strategy:

        std::string symbol = "NVDA";

        // Create the contract and order
        Contract contract = createStockContract(symbol);
        Order order = createLimitOrder("BUY", 100, 130.00);

        // Place the order
        wrapper.client.placeOrder(1, contract, order);

        std::cout << "Order placed for " << symbol << std::endl;

    } else {
        std::cout << "Failed to connect to TWS." << std::endl;
    }

    wrapper.client.eDisconnect();
    return 0;
}
