#include <iostream>
#include <chrono>
#include <thread>
#include <vector>
#include <map>
#include <string>
#include <atomic>
#include <mutex>
#include <zmq.h>
#include <fstream>
#include <iomanip>
#include <algorithm>
#include <numeric>
#include <cmath>

// Include our trading system components
#include "signal_parser.h"
#include "order_manager.h"
#include "position_tracker.h"
#include "risk_checker.h"
#include "simple_json_parser.h"

struct LatencyMeasurement {
    std::string signal_id;
    
    // Timing points (high-resolution clock)
    std::chrono::high_resolution_clock::time_point zmq_receive_start;
    std::chrono::high_resolution_clock::time_point zmq_receive_end;
    std::chrono::high_resolution_clock::time_point json_parsing_start;
    std::chrono::high_resolution_clock::time_point json_parsing_end;
    std::chrono::high_resolution_clock::time_point signal_validation_start;
    std::chrono::high_resolution_clock::time_point signal_validation_end;
    std::chrono::high_resolution_clock::time_point risk_check_start;
    std::chrono::high_resolution_clock::time_point risk_check_end;
    std::chrono::high_resolution_clock::time_point order_creation_start;
    std::chrono::high_resolution_clock::time_point order_creation_end;
    std::chrono::high_resolution_clock::time_point tws_simulation_start;
    std::chrono::high_resolution_clock::time_point tws_simulation_end;
    
    std::string error_message;
    
    // Calculate latencies in microseconds
    double getZmqReceiveLatency() const {
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
            zmq_receive_end - zmq_receive_start);
        return duration.count() / 1000.0; // Convert to microseconds
    }
    
    double getJsonParsingLatency() const {
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
            json_parsing_end - json_parsing_start);
        return duration.count() / 1000.0;
    }
    
    double getSignalValidationLatency() const {
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
            signal_validation_end - signal_validation_start);
        return duration.count() / 1000.0;
    }
    
    double getRiskCheckLatency() const {
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
            risk_check_end - risk_check_start);
        return duration.count() / 1000.0;
    }
    
    double getOrderCreationLatency() const {
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
            order_creation_end - order_creation_start);
        return duration.count() / 1000.0;
    }
    
    double getTwsSimulationLatency() const {
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
            tws_simulation_end - tws_simulation_start);
        return duration.count() / 1000.0;
    }
    
    double getTotalCppLatency() const {
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
            tws_simulation_end - zmq_receive_start);
        return duration.count() / 1000.0;
    }
};

class LatencyTestSubscriber {
private:
    std::string host_;
    int port_;
    void* context_;
    void* socket_;
    std::atomic<bool> running_;
    std::thread receive_thread_;
    std::vector<LatencyMeasurement> measurements_;
    mutable std::mutex measurements_mutex_;
    
    // Components for realistic processing simulation
    std::unique_ptr<RiskChecker> risk_checker_;
    std::unique_ptr<PositionTracker> position_tracker_;
    
public:
    LatencyTestSubscriber(const std::string& host, int port) 
        : host_(host), port_(port), context_(nullptr), socket_(nullptr), running_(false) {
        
        // Initialize components
        risk_checker_ = std::make_unique<RiskChecker>();
        position_tracker_ = std::make_unique<PositionTracker>();
        
        std::cout << "Latency test subscriber initialized" << std::endl;
    }
    
    ~LatencyTestSubscriber() {
        stop();
    }
    
    bool connect() {
        context_ = zmq_ctx_new();
        if (!context_) {
            std::cerr << "Failed to create ZMQ context" << std::endl;
            return false;
        }
        
        socket_ = zmq_socket(context_, ZMQ_SUB);
        if (!socket_) {
            std::cerr << "Failed to create ZMQ socket" << std::endl;
            return false;
        }
        
        // Set receive timeout
        int timeout = 100; // 100ms
        zmq_setsockopt(socket_, ZMQ_RCVTIMEO, &timeout, sizeof(timeout));
        
        // Subscribe to trade signals
        zmq_setsockopt(socket_, ZMQ_SUBSCRIBE, "TRADE_SIGNAL", 11);
        
        std::string endpoint = "tcp://" + host_ + ":" + std::to_string(port_);
        if (zmq_connect(socket_, endpoint.c_str()) != 0) {
            std::cerr << "Failed to connect to " << endpoint << std::endl;
            return false;
        }
        
        std::cout << "Connected to ZMQ publisher at " << endpoint << std::endl;
        return true;
    }
    
    void start() {
        if (running_.load()) return;
        
        running_ = true;
        receive_thread_ = std::thread(&LatencyTestSubscriber::receiveLoop, this);
        std::cout << "Started latency measurement receiver" << std::endl;
    }
    
    void stop() {
        if (!running_.load()) return;
        
        running_ = false;
        if (receive_thread_.joinable()) {
            receive_thread_.join();
        }
        
        if (socket_) {
            zmq_close(socket_);
            socket_ = nullptr;
        }
        
        if (context_) {
            zmq_ctx_destroy(context_);
            context_ = nullptr;
        }
        
        std::cout << "Stopped latency measurement receiver" << std::endl;
    }
    
    std::vector<LatencyMeasurement> getMeasurements() const {
        std::lock_guard<std::mutex> lock(measurements_mutex_);
        return measurements_;
    }
    
private:
    void receiveLoop() {
        std::cout << "Entering receive loop..." << std::endl;
        
        while (running_.load()) {
            LatencyMeasurement measurement;
            
            // ZMQ receive timing
            measurement.zmq_receive_start = std::chrono::high_resolution_clock::now();
            
            char topic[256];
            int topic_size = zmq_recv(socket_, topic, sizeof(topic) - 1, 0);
            if (topic_size == -1) {
                if (errno == EAGAIN) {
                    // Timeout - continue
                    continue;
                }
                std::cerr << "ZMQ receive error: " << zmq_strerror(errno) << std::endl;
                break;
            }
            topic[topic_size] = '\0';
            
            char message[4096];
            int message_size = zmq_recv(socket_, message, sizeof(message) - 1, 0);
            if (message_size == -1) {
                std::cerr << "ZMQ message receive error: " << zmq_strerror(errno) << std::endl;
                continue;
            }
            message[message_size] = '\0';
            
            measurement.zmq_receive_end = std::chrono::high_resolution_clock::now();
            
            // Process the message
            processMessage(message, measurement);
            
            // Store measurement
            {
                std::lock_guard<std::mutex> lock(measurements_mutex_);
                measurements_.push_back(measurement);
            }
        }
    }
    
    void processMessage(const std::string& message, LatencyMeasurement& measurement) {
        try {
            // JSON parsing timing
            measurement.json_parsing_start = std::chrono::high_resolution_clock::now();
            
            auto j = SimpleJsonParser::parse(message);
            
            // Extract signal ID
            measurement.signal_id = j.contains("message_id") ? j["message_id"].asString() : "unknown";
            
            // Extract signal data
            std::string pair_name = j.contains("pair_name") ? j["pair_name"].asString() : "";
            std::string signal_type = j.contains("signal_type") ? j["signal_type"].asString() : "";
            double z_score = j.contains("z_score") ? j["z_score"].asDouble() : 0.0;
            double confidence = j.contains("confidence") ? j["confidence"].asDouble() : 0.0;
            int shares_a = j.contains("shares_a") ? j["shares_a"].asInt() : 0;
            int shares_b = j.contains("shares_b") ? j["shares_b"].asInt() : 0;
            double volatility = j.contains("volatility") ? j["volatility"].asDouble() : 0.0;
            double correlation = j.contains("correlation") ? j["correlation"].asDouble() : 0.0;
            
            measurement.json_parsing_end = std::chrono::high_resolution_clock::now();
            
            // Signal validation timing
            measurement.signal_validation_start = std::chrono::high_resolution_clock::now();
            
            // Validate required fields
            bool valid = !pair_name.empty() && 
                        !signal_type.empty() && 
                        confidence > 0.0 && 
                        confidence <= 1.0 &&
                        abs(z_score) <= 10.0;
            
            measurement.signal_validation_end = std::chrono::high_resolution_clock::now();
            
            if (!valid) {
                measurement.error_message = "Signal validation failed";
                return;
            }
            
            // Risk check timing
            measurement.risk_check_start = std::chrono::high_resolution_clock::now();
            
            // Create TradeSignal object for risk checking
            TradeSignal signal;
            signal.pairName = pair_name;
            signal.signalType = signal_type;
            signal.zScore = z_score;
            signal.confidence = confidence;
            signal.sharesA = shares_a;
            signal.sharesB = shares_b;
            signal.volatility = volatility;
            signal.correlation = correlation;
            
            bool risk_passed = risk_checker_->checkSignalRisk(signal);
            
            measurement.risk_check_end = std::chrono::high_resolution_clock::now();
            
            if (!risk_passed) {
                measurement.error_message = "Risk check failed";
                return;
            }
            
            // Order creation timing
            measurement.order_creation_start = std::chrono::high_resolution_clock::now();
            
            // Create order requests (simulate order manager)
            std::vector<OrderRequest> orders;
            
            if (shares_a != 0) {
                OrderRequest order_a;
                order_a.symbol = "TEST_A";
                order_a.action = (shares_a > 0) ? "BUY" : "SELL";
                order_a.quantity = abs(shares_a);
                order_a.orderType = "MKT";
                order_a.limitPrice = 0.0;
                order_a.orderId = 0;
                orders.push_back(order_a);
            }
            
            if (shares_b != 0) {
                OrderRequest order_b;
                order_b.symbol = "TEST_B";
                order_b.action = (shares_b > 0) ? "BUY" : "SELL";
                order_b.quantity = abs(shares_b);
                order_b.orderType = "MKT";
                order_b.limitPrice = 0.0;
                order_b.orderId = 0;
                orders.push_back(order_b);
            }
            
            measurement.order_creation_end = std::chrono::high_resolution_clock::now();
            
            // TWS simulation timing
            measurement.tws_simulation_start = std::chrono::high_resolution_clock::now();
            
            // Simulate TWS order submission (network delay + processing)
            std::this_thread::sleep_for(std::chrono::microseconds(5000)); // 5ms simulation
            
            measurement.tws_simulation_end = std::chrono::high_resolution_clock::now();
            
        } catch (const std::exception& e) {
            measurement.error_message = std::string("Processing error: ") + e.what();
        }
    }
};

class LatencyAnalyzer {
public:
    static void analyzeMeasurements(const std::vector<LatencyMeasurement>& measurements) {
        if (measurements.empty()) {
            std::cout << "No measurements to analyze" << std::endl;
            return;
        }
        
        std::cout << "\n" << std::string(80, '=') << std::endl;
        std::cout << "C++ LATENCY MEASUREMENT REPORT" << std::endl;
        std::cout << std::string(80, '=') << std::endl;
        
        // Extract latencies
        std::vector<double> zmq_latencies, json_latencies, validation_latencies;
        std::vector<double> risk_latencies, order_latencies, tws_latencies, total_latencies;
        
        for (const auto& m : measurements) {
            zmq_latencies.push_back(m.getZmqReceiveLatency());
            json_latencies.push_back(m.getJsonParsingLatency());
            validation_latencies.push_back(m.getSignalValidationLatency());
            risk_latencies.push_back(m.getRiskCheckLatency());
            order_latencies.push_back(m.getOrderCreationLatency());
            tws_latencies.push_back(m.getTwsSimulationLatency());
            total_latencies.push_back(m.getTotalCppLatency());
        }
        
        // Calculate statistics
        auto stats = [](const std::vector<double>& data) -> std::map<std::string, double> {
            if (data.empty()) return {};
            
            std::vector<double> sorted = data;
            std::sort(sorted.begin(), sorted.end());
            
            return {
                {"count", static_cast<double>(data.size())},
                {"mean", std::accumulate(data.begin(), data.end(), 0.0) / data.size()},
                {"median", sorted[sorted.size() / 2]},
                {"min", sorted.front()},
                {"max", sorted.back()},
                {"p50", sorted[static_cast<size_t>(sorted.size() * 0.5)]},
                {"p90", sorted[static_cast<size_t>(sorted.size() * 0.9)]},
                {"p95", sorted[static_cast<size_t>(sorted.size() * 0.95)]},
                {"p99", sorted[static_cast<size_t>(sorted.size() * 0.99)]}
            };
        };
        
        // Print statistics
        std::cout << "\nC++ LATENCY BREAKDOWN (All times in microseconds)" << std::endl;
        std::cout << std::string(80, '-') << std::endl;
        
        printStageStats("ZMQ Receive", stats(zmq_latencies));
        printStageStats("JSON Parsing", stats(json_latencies));
        printStageStats("Signal Validation", stats(validation_latencies));
        printStageStats("Risk Check", stats(risk_latencies));
        printStageStats("Order Creation", stats(order_latencies));
        printStageStats("TWS Simulation", stats(tws_latencies));
        
        std::cout << "\nTOTAL C++ LATENCY ANALYSIS:" << std::endl;
        std::cout << std::string(80, '-') << std::endl;
        
        auto total_stats = stats(total_latencies);
        printStageStats("Total C++ Processing", total_stats);
        
        // Performance assessment
        double avg_ms = total_stats["mean"] / 1000.0;
        std::cout << "\nPERFORMANCE ASSESSMENT:" << std::endl;
        if (avg_ms < 1) {
            std::cout << "   EXCELLENT - Sub-millisecond C++ processing!" << std::endl;
        } else if (avg_ms < 5) {
            std::cout << "   GOOD - Competitive C++ latency" << std::endl;
        } else if (avg_ms < 10) {
            std::cout << "   ACCEPTABLE - Room for C++ optimization" << std::endl;
        } else {
            std::cout << "   NEEDS IMPROVEMENT - High C++ latency detected" << std::endl;
        }
        
        // Save detailed results
        saveDetailedResults(measurements);
        
        std::cout << "\n" << std::string(80, '=') << std::endl;
    }
    
private:
    static void printStageStats(const std::string& stage, const std::map<std::string, double>& stats) {
        if (stats.empty()) return;
        
        std::cout << "\n" << stage << ":" << std::endl;
        std::cout << "   Count: " << static_cast<int>(stats.at("count")) << std::endl;
        std::cout << "   Mean:   " << std::fixed << std::setprecision(2) << stats.at("mean") << " μs" << std::endl;
        std::cout << "   Median: " << std::fixed << std::setprecision(2) << stats.at("median") << " μs" << std::endl;
        std::cout << "   Min:    " << std::fixed << std::setprecision(2) << stats.at("min") << " μs" << std::endl;
        std::cout << "   Max:    " << std::fixed << std::setprecision(2) << stats.at("max") << " μs" << std::endl;
        std::cout << "   P50:    " << std::fixed << std::setprecision(2) << stats.at("p50") << " μs" << std::endl;
        std::cout << "   P90:    " << std::fixed << std::setprecision(2) << stats.at("p90") << " μs" << std::endl;
        std::cout << "   P95:    " << std::fixed << std::setprecision(2) << stats.at("p95") << " μs" << std::endl;
        std::cout << "   P99:    " << std::fixed << std::setprecision(2) << stats.at("p99") << " μs" << std::endl;
    }
    
    static void saveDetailedResults(const std::vector<LatencyMeasurement>& measurements) {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << "cpp_latency_results_" << std::put_time(std::localtime(&time_t), "%Y%m%d_%H%M%S") << ".json";
        
        // Create a simple JSON string instead of using nlohmann::json
        std::ofstream file(ss.str());
        if (!file.is_open()) {
            std::cerr << "Failed to open file for writing: " << ss.str() << std::endl;
            return;
        }
        
        file << "{\n";
        file << "  \"test_info\": {\n";
        file << "    \"timestamp\": \"" << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S") << "\",\n";
        file << "    \"total_measurements\": " << measurements.size() << ",\n";
        file << "    \"valid_measurements\": " << std::count_if(measurements.begin(), measurements.end(), 
            [](const LatencyMeasurement& m) { return m.error_message.empty(); }) << "\n";
        file << "  },\n";
        file << "  \"measurements\": [\n";
        
        for (size_t i = 0; i < measurements.size(); ++i) {
            const auto& m = measurements[i];
            file << "    {\n";
            file << "      \"signal_id\": \"" << m.signal_id << "\",\n";
            file << "      \"zmq_receive_latency\": " << m.getZmqReceiveLatency() << ",\n";
            file << "      \"json_parsing_latency\": " << m.getJsonParsingLatency() << ",\n";
            file << "      \"signal_validation_latency\": " << m.getSignalValidationLatency() << ",\n";
            file << "      \"risk_check_latency\": " << m.getRiskCheckLatency() << ",\n";
            file << "      \"order_creation_latency\": " << m.getOrderCreationLatency() << ",\n";
            file << "      \"tws_simulation_latency\": " << m.getTwsSimulationLatency() << ",\n";
            file << "      \"total_cpp_latency\": " << m.getTotalCppLatency() << ",\n";
            file << "      \"error_message\": \"" << m.error_message << "\"\n";
            file << "    }";
            if (i < measurements.size() - 1) file << ",";
            file << "\n";
        }
        
        file << "  ]\n";
        file << "}\n";
        file.close();
        
        std::cout << "   Detailed results saved to: " << ss.str() << std::endl;
    }
};

void runCppLatencyTest(int port = 5555, int duration_seconds = 30) {
    std::cout << "Starting C++ Latency Measurement Test" << std::endl;
    std::cout << "   Port: " << port << std::endl;
    std::cout << "   Duration: " << duration_seconds << " seconds" << std::endl;
    
    LatencyTestSubscriber subscriber("localhost", port);
    
    if (!subscriber.connect()) {
        std::cerr << "Failed to connect subscriber" << std::endl;
        return;
    }
    
    subscriber.start();
    
    std::cout << "\nListening for signals from Python..." << std::endl;
    std::cout << "   Press Ctrl+C to stop early" << std::endl;
    
    // Wait for specified duration
    auto start_time = std::chrono::steady_clock::now();
    while (std::chrono::steady_clock::now() - start_time < std::chrono::seconds(duration_seconds)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        // Print progress
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now() - start_time).count();
        auto remaining = duration_seconds - elapsed;
        
        std::cout << "\r   Elapsed: " << elapsed << "s, Remaining: " << remaining << "s" << std::flush;
    }
    
    std::cout << "\n\nStopping test..." << std::endl;
    subscriber.stop();
    
    // Analyze results
    auto measurements = subscriber.getMeasurements();
    std::cout << "\nCollected " << measurements.size() << " measurements" << std::endl;
    
    LatencyAnalyzer::analyzeMeasurements(measurements);
}

int main(int argc, char* argv[]) {
    int port = 5555;
    int duration = 30;
    
    if (argc > 1) {
        port = std::stoi(argv[1]);
    }
    if (argc > 2) {
        duration = std::stoi(argv[2]);
    }
    
    try {
        runCppLatencyTest(port, duration);
    } catch (const std::exception& e) {
        std::cerr << "Test failed with error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
} 