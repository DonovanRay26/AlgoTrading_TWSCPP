#include "tws_integration/MyWrapper.h"
#include "tws_integration/OrderUtils.h"
#include "signal_watcher.h"
#include "order_manager.h"
#include <thread>
#include <chrono>
#include <iostream>
#include <signal.h>

// Global variables for cleanup
SignalWatcher* g_signalWatcher = nullptr;
OrderManager* g_orderManager = nullptr;
MyWrapper* g_wrapper = nullptr;
bool g_running = true;

// Signal handler for graceful shutdown
void signalHandler(int signum) {
    std::cout << "\nReceived signal " << signum << ", shutting down gracefully..." << std::endl;
    g_running = false;
}

int main() {
    // Set up signal handlers
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    std::cout << "=== C++ Pairs Trading Order Execution Engine ===" << std::endl;
    
    try {
        // Initialize TWS wrapper
        MyWrapper wrapper;
        g_wrapper = &wrapper;
        
        // Connect to TWS
        std::cout << "Connecting to TWS..." << std::endl;
        if (wrapper.client.eConnect("127.0.0.1", 7497, 0)) {
            std::cout << "TWS connection initiated, waiting for connection..." << std::endl;
        } else {
            std::cerr << "Failed to initiate TWS connection" << std::endl;
            return 1;
        }
        
        // Wait for connection
        std::this_thread::sleep_for(std::chrono::seconds(2));
        
        if (!wrapper.client.isConnected()) {
            std::cerr << "Failed to connect to TWS. Please ensure TWS is running and API connections are enabled." << std::endl;
            return 1;
        }
        
        std::cout << "Successfully connected to TWS!" << std::endl;
        
        // Initialize order manager
        OrderManager orderManager(wrapper);
        g_orderManager = &orderManager;
        
        // Set up TWS wrapper to forward callbacks to order manager
        wrapper.setOrderManager(&orderManager);
        
        // Initialize signal watcher
        SignalWatcher signalWatcher("localhost", 5555);  // Default ZMQ port
        g_signalWatcher = &signalWatcher;
        
        // Set up callback from signal watcher to order manager
        signalWatcher.setOrderManagerCallback(
            [&orderManager](const TradeSignal& signal) {
                orderManager.handleTradeSignal(signal);
            }
        );
        
        // Start components
        std::cout << "Starting order manager..." << std::endl;
        orderManager.start();
        
        std::cout << "Starting signal watcher..." << std::endl;
        signalWatcher.start();
        
        std::cout << "Order execution engine is running. Press Ctrl+C to stop." << std::endl;
        std::cout << "Waiting for signals from Python data engine..." << std::endl;
        
        // Main loop
        while (g_running) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            
            // Check connection status
            if (!wrapper.client.isConnected()) {
                std::cerr << "Lost connection to TWS!" << std::endl;
                break;
            }
            
            if (!signalWatcher.isConnected()) {
                std::cerr << "Lost connection to Python data engine!" << std::endl;
                break;
            }
        }
        
    } catch (const std::exception& e) {
        std::cerr << "Fatal error: " << e.what() << std::endl;
        return 1;
    }
    
    // Cleanup
    std::cout << "Shutting down..." << std::endl;
    
    if (g_signalWatcher) {
        g_signalWatcher->stop();
    }
    
    if (g_orderManager) {
        g_orderManager->stop();
    }
    
    if (g_wrapper) {
        g_wrapper->client.eDisconnect();
    }
    
    std::cout << "Order execution engine stopped." << std::endl;
    return 0;
}
