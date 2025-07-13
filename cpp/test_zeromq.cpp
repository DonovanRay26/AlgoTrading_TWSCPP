#include <iostream>
#include <zmq.h>
#include <string>
#include <thread>
#include <chrono>
#include <cstring>

int main() {
    std::cout << "Testing ZeroMQ installation..." << std::endl;
    
    void* context = nullptr;
    void* publisher = nullptr;
    void* subscriber = nullptr;
    
    try {
        // Create ZMQ context
        context = zmq_ctx_new();
        if (!context) {
            throw std::runtime_error("Failed to create ZMQ context");
        }
        std::cout << "ZMQ context created successfully" << std::endl;
        
        // Create a publisher socket
        publisher = zmq_socket(context, ZMQ_PUB);
        if (!publisher) {
            throw std::runtime_error("Failed to create publisher socket");
        }
        std::cout << "Publisher socket created successfully" << std::endl;
        
        // Create a subscriber socket
        subscriber = zmq_socket(context, ZMQ_SUB);
        if (!subscriber) {
            throw std::runtime_error("Failed to create subscriber socket");
        }
        std::cout << "Subscriber socket created successfully" << std::endl;
        
        // Bind publisher to a port
        int rc = zmq_bind(publisher, "tcp://*:5555");
        if (rc != 0) {
            throw std::runtime_error("Failed to bind publisher to port 5555");
        }
        std::cout << "Publisher bound to port 5555" << std::endl;
        
        // Connect subscriber to the publisher
        rc = zmq_connect(subscriber, "tcp://localhost:5555");
        if (rc != 0) {
            throw std::runtime_error("Failed to connect subscriber to publisher");
        }
        std::cout << "Subscriber connected to publisher" << std::endl;
        
        // Subscribe to all topics
        rc = zmq_setsockopt(subscriber, ZMQ_SUBSCRIBE, "", 0);
        if (rc != 0) {
            throw std::runtime_error("Failed to set subscribe option");
        }
        std::cout << "Subscriber subscribed to all topics" << std::endl;
        
        // Set receive timeout
        int timeout = 2000; // 2 seconds
        rc = zmq_setsockopt(subscriber, ZMQ_RCVTIMEO, &timeout, sizeof(timeout));
        if (rc != 0) {
            throw std::runtime_error("Failed to set receive timeout");
        }
        
        // CRITICAL: Wait for subscriber to be ready
        std::cout << "Waiting for subscriber to be ready..." << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        // Send a test message
        std::string testMessage = "Hello ZeroMQ!";
        rc = zmq_send(publisher, "TEST", 4, ZMQ_SNDMORE);
        if (rc == -1) {
            throw std::runtime_error("Failed to send topic");
        }
        rc = zmq_send(publisher, testMessage.c_str(), testMessage.length(), 0);
        if (rc == -1) {
            throw std::runtime_error("Failed to send message");
        }
        std::cout << "Test message sent: " << testMessage << std::endl;
        
        // Small delay to ensure message is sent
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        
        // Receive the message
        char topicBuffer[256];
        char messageBuffer[4096];
        
        int topicSize = zmq_recv(subscriber, topicBuffer, sizeof(topicBuffer) - 1, 0);
        if (topicSize == -1) {
            if (zmq_errno() == EAGAIN) {
                throw std::runtime_error("Timeout waiting for message - subscriber may not be ready");
            }
            throw std::runtime_error("Failed to receive topic: " + std::string(zmq_strerror(zmq_errno())));
        }
        topicBuffer[topicSize] = '\0';
        
        int messageSize = zmq_recv(subscriber, messageBuffer, sizeof(messageBuffer) - 1, 0);
        if (messageSize == -1) {
            if (zmq_errno() == EAGAIN) {
                throw std::runtime_error("Timeout waiting for message body");
            }
            throw std::runtime_error("Failed to receive message: " + std::string(zmq_strerror(zmq_errno())));
        }
        messageBuffer[messageSize] = '\0';
        
        std::string topic(topicBuffer);
        std::string message(messageBuffer);
        std::cout << "Test message received: " << message << std::endl;
        
        // Verify message content
        if (message == testMessage) {
            std::cout << "Message content verified correctly" << std::endl;
        } else {
            std::cout << "Message content verification failed" << std::endl;
            return 1;
        }
        
        // Test different message types
        std::cout << "\nTesting different message types..." << std::endl;
        
        // Test trade signal message
        std::string tradeSignal = R"({
            "message_id": "test_001",
            "timestamp": "2024-01-01T10:00:00",
            "message_type": "TRADE_SIGNAL",
            "pair_name": "AAPL_MSFT",
            "signal_type": "ENTER_LONG_SPREAD",
            "confidence": 0.85
        })";
        
        rc = zmq_send(publisher, "TRADE_SIGNAL", 12, ZMQ_SNDMORE);
        if (rc == -1) {
            throw std::runtime_error("Failed to send trade signal topic");
        }
        rc = zmq_send(publisher, tradeSignal.c_str(), tradeSignal.length(), 0);
        if (rc == -1) {
            throw std::runtime_error("Failed to send trade signal");
        }
        std::cout << "Trade signal sent" << std::endl;
        
        // Small delay
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        
        // Receive trade signal
        topicSize = zmq_recv(subscriber, topicBuffer, sizeof(topicBuffer) - 1, 0);
        if (topicSize == -1) {
            if (zmq_errno() == EAGAIN) {
                throw std::runtime_error("Timeout waiting for trade signal topic");
            }
            throw std::runtime_error("Failed to receive trade signal topic");
        }
        topicBuffer[topicSize] = '\0';
        
        messageSize = zmq_recv(subscriber, messageBuffer, sizeof(messageBuffer) - 1, 0);
        if (messageSize == -1) {
            if (zmq_errno() == EAGAIN) {
                throw std::runtime_error("Timeout waiting for trade signal body");
            }
            throw std::runtime_error("Failed to receive trade signal");
        }
        messageBuffer[messageSize] = '\0';
        
        std::string receivedTopic(topicBuffer);
        std::string receivedSignal(messageBuffer);
        std::cout << "Trade signal received on topic: " << receivedTopic << std::endl;
        
        // Test heartbeat message
        std::string heartbeat = R"({
            "message_id": "hb_001",
            "timestamp": "2024-01-01T10:00:00",
            "message_type": "HEARTBEAT"
        })";
        
        rc = zmq_send(publisher, "HEARTBEAT", 9, ZMQ_SNDMORE);
        if (rc == -1) {
            throw std::runtime_error("Failed to send heartbeat topic");
        }
        rc = zmq_send(publisher, heartbeat.c_str(), heartbeat.length(), 0);
        if (rc == -1) {
            throw std::runtime_error("Failed to send heartbeat");
        }
        std::cout << "Heartbeat sent" << std::endl;
        
        // Small delay
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        
        // Receive heartbeat
        topicSize = zmq_recv(subscriber, topicBuffer, sizeof(topicBuffer) - 1, 0);
        if (topicSize == -1) {
            if (zmq_errno() == EAGAIN) {
                throw std::runtime_error("Timeout waiting for heartbeat topic");
            }
            throw std::runtime_error("Failed to receive heartbeat topic");
        }
        topicBuffer[topicSize] = '\0';
        
        messageSize = zmq_recv(subscriber, messageBuffer, sizeof(messageBuffer) - 1, 0);
        if (messageSize == -1) {
            if (zmq_errno() == EAGAIN) {
                throw std::runtime_error("Timeout waiting for heartbeat body");
            }
            throw std::runtime_error("Failed to receive heartbeat");
        }
        messageBuffer[messageSize] = '\0';
        
        std::string hbTopic(topicBuffer);
        std::string hbMessage(messageBuffer);
        std::cout << "Heartbeat received on topic: " << hbTopic << std::endl;
        
        std::cout << "\nAll ZeroMQ tests passed!" << std::endl;
        std::cout << "ZeroMQ is working correctly and ready for the trading system." << std::endl;
        
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        
        // Cleanup
        if (subscriber) zmq_close(subscriber);
        if (publisher) zmq_close(publisher);
        if (context) zmq_ctx_destroy(context);
        
        return 1;
    }
    
    // Cleanup on success
    if (subscriber) zmq_close(subscriber);
    if (publisher) zmq_close(publisher);
    if (context) zmq_ctx_destroy(context);
} 