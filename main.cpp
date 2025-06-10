#include "MyWrapper.h"
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
    } else {
        std::cout << "Failed to connect to TWS." << std::endl;
    }

    wrapper.client.eDisconnect();
    return 0;
}
