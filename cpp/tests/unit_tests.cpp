#include <iostream>
#include <cassert>
#include <string>
#include <cmath>
#include "../include/simple_json_parser.h"
#include "../include/signal_parser.h"
#include "../include/order_manager.h"
#include "../include/position_tracker.h"
#include "../include/risk_checker.h"

// Test utilities - FIXED: changed ASSERT to assert
void assertEqual(const std::string& actual, const std::string& expected, const std::string& testName) {
    if (actual != expected) {
        std::cerr << "FAILED: " << testName << " - Expected '" << expected << "', got '" << actual << "'" << std::endl;
    } else {
        std::cout << "PASSED: " << testName << std::endl;
    }
}

void assertEqual(double actual, double expected, const std::string& testName, double tolerance = 0.001) {
    if (std::abs(actual - expected) > tolerance) {
        std::cerr << "FAILED: " << testName << " - Expected " << expected << ", got " << actual << std::endl;
    } else {
        std::cout << "PASSED: " << testName << std::endl;
    }
}

void assertEqual(int actual, int expected, const std::string& testName) {
    if (actual != expected) {
        std::cerr << "FAILED: " << testName << " - Expected " << expected << ", got " << actual << std::endl;
    } else {
        std::cout << "PASSED: " << testName << std::endl;
    }
}

void assertTrue(bool condition, const std::string& testName) {
    if (!condition) {
        std::cerr << "FAILED: " << testName << std::endl;
    } else {
        std::cout << "PASSED: " << testName << std::endl;
    }
}

// JSON Parser Tests
void testJsonParser() {
    std::cout << "\n=== Testing JSON Parser ===" << std::endl;
    
    // Test simple string
    auto json1 = SimpleJsonParser::parse("\"hello world\"");
    assertEqual(json1.asString(), "hello world", "Simple string parsing");
    
    // Test number
    auto json2 = SimpleJsonParser::parse("42.5");
    assertEqual(json2.asDouble(), 42.5, "Number parsing");
    
    // Test boolean
    auto json3 = SimpleJsonParser::parse("true");
    assertTrue(json3.asBool(), "Boolean true parsing");
    
    auto json4 = SimpleJsonParser::parse("false");
    assertTrue(!json4.asBool(), "Boolean false parsing");
    
    // Test object
    auto json5 = SimpleJsonParser::parse("{\"key\": \"value\", \"number\": 123}");
    assertEqual(json5["key"].asString(), "value", "Object string value");
    assertEqual(json5["number"].asInt(), 123, "Object number value");
    assertTrue(json5.contains("key"), "Object contains check");
    assertTrue(!json5.contains("missing"), "Object missing key check");
    
    // Test array
    auto json6 = SimpleJsonParser::parse("[1, 2, 3]");
    assertEqual(json6.size(), 3, "Array size");
    assertEqual(json6[0].asInt(), 1, "Array first element");
    assertEqual(json6[1].asInt(), 2, "Array second element");
    assertEqual(json6[2].asInt(), 3, "Array third element");
    
    // Test nested structure
    auto json7 = SimpleJsonParser::parse("{\"data\": {\"items\": [1, 2, 3]}}");
    assertEqual(json7["data"]["items"][0].asInt(), 1, "Nested object and array");
    
    std::cout << "All JSON parser tests passed!" << std::endl;
}

// Signal Parser Tests
void testSignalParser() {
    std::cout << "\n=== Testing Signal Parser ===" << std::endl;
    
    SignalParser parser;
    
    // Test trade signal parsing
    std::string tradeSignalJson = R"({
        "message_id": "test_123",
        "timestamp": "2024-01-01T10:00:00",
        "message_type": "TRADE_SIGNAL",
        "pair_name": "AAPL_MSFT",
        "symbol_a": "AAPL",
        "symbol_b": "MSFT",
        "signal_type": "ENTER_LONG_SPREAD",
        "z_score": 1.5,
        "hedge_ratio": 0.8,
        "confidence": 0.85,
        "position_size": 1000,
        "shares_a": 100,
        "shares_b": -80,
        "volatility": 0.25,
        "correlation": 0.75
    })";
    
    auto signal = parser.parseTradeSignal(tradeSignalJson);
    assertEqual(signal.messageId, "test_123", "Trade signal message ID");
    assertEqual(signal.pairName, "AAPL_MSFT", "Trade signal pair name");
    assertEqual(signal.signalType, "ENTER_LONG_SPREAD", "Trade signal type");
    assertEqual(signal.zScore, 1.5, "Trade signal z-score");
    assertEqual(signal.confidence, 0.85, "Trade signal confidence");
    assertEqual(signal.sharesA, 100, "Trade signal shares A");
    assertEqual(signal.sharesB, -80, "Trade signal shares B");
    
    // Test message type detection
    auto messageType = parser.getMessageType(tradeSignalJson);
    assertTrue(messageType == MessageType::TRADE_SIGNAL, "Message type detection");
    
    // Test invalid message
    assertTrue(!parser.isValidMessage("invalid json"), "Invalid message detection");
    
    std::cout << "All signal parser tests passed!" << std::endl;
}

// Position Tracker Tests
void testPositionTracker() {
    std::cout << "\n=== Testing Position Tracker ===" << std::endl;
    
    PositionTracker tracker;
    
    // Test buying shares
    tracker.updatePosition("AAPL", "BUY", 100, 150.0);
    auto positions = tracker.getAllPositions();
    assertEqual(positions["AAPL"], 100.0, "Buy position tracking");
    
    // Test selling shares
    tracker.updatePosition("AAPL", "SELL", 50, 155.0);
    positions = tracker.getAllPositions();
    assertEqual(positions["AAPL"], 50.0, "Sell position tracking");
    
    // Test short position
    tracker.updatePosition("MSFT", "SELL", 200, 300.0);
    positions = tracker.getAllPositions();
    assertEqual(positions["MSFT"], -200.0, "Short position tracking");
    
    // Test covering short
    tracker.updatePosition("MSFT", "BUY", 100, 295.0);
    positions = tracker.getAllPositions();
    assertEqual(positions["MSFT"], -100.0, "Cover short position tracking");
    
    // Test P&L calculations
    std::map<std::string, double> prices = {{"AAPL", 160.0}, {"MSFT", 290.0}};
    tracker.updateMarketPrices(prices);
    
    double aaplPnl = tracker.getUnrealizedPnl("AAPL");
    double msftPnl = tracker.getUnrealizedPnl("MSFT");
    
    // AAPL: 50 shares * (160 - 150) = 500 profit
    assertEqual(aaplPnl, 500.0, "AAPL unrealized P&L");
    // MSFT: 100 shares * (300 - 290) = 1000 profit (short)
    assertEqual(msftPnl, 1000.0, "MSFT unrealized P&L");
    
    std::cout << "All position tracker tests passed!" << std::endl;
}

// Risk Checker Tests
void testRiskChecker() {
    std::cout << "\n=== Testing Risk Checker ===" << std::endl;
    
    RiskChecker checker;
    
    // Test valid signal
    TradeSignal validSignal;
    validSignal.confidence = 0.8;
    validSignal.zScore = 1.5;
    validSignal.sharesA = 100;
    validSignal.sharesB = -80;
    validSignal.correlation = 0.7;
    validSignal.volatility = 0.2;
    
    assertTrue(checker.checkSignalRisk(validSignal), "Valid signal risk check");
    
    // Test low confidence
    TradeSignal lowConfidenceSignal = validSignal;
    lowConfidenceSignal.confidence = 0.5;  // Below 0.7 threshold
    assertTrue(!checker.checkSignalRisk(lowConfidenceSignal), "Low confidence rejection");
    
    // Test high z-score
    TradeSignal highZScoreSignal = validSignal;
    highZScoreSignal.zScore = 4.0;  // Above 3.0 threshold
    assertTrue(!checker.checkSignalRisk(highZScoreSignal), "High z-score rejection");
    
    // Test large position
    TradeSignal largePositionSignal = validSignal;
    largePositionSignal.sharesA = 15000;  // Above 10000 threshold
    assertTrue(!checker.checkSignalRisk(largePositionSignal), "Large position rejection");
    
    // Test high correlation
    TradeSignal highCorrelationSignal = validSignal;
    highCorrelationSignal.correlation = 0.98;  // Above 0.95 threshold
    assertTrue(!checker.checkSignalRisk(highCorrelationSignal), "High correlation rejection");
    
    // Test high volatility
    TradeSignal highVolatilitySignal = validSignal;
    highVolatilitySignal.volatility = 0.6;  // Above 0.5 threshold
    assertTrue(!checker.checkSignalRisk(highVolatilitySignal), "High volatility rejection");
    
    std::cout << "All risk checker tests passed!" << std::endl;
}

// Integration Tests
void testIntegration() {
    std::cout << "\n=== Testing Integration ===" << std::endl;
    
    // Test end-to-end signal processing
    std::string testSignalJson = R"({
        "message_id": "integration_test",
        "timestamp": "2024-01-01T10:00:00",
        "message_type": "TRADE_SIGNAL",
        "pair_name": "AAPL_MSFT",
        "symbol_a": "AAPL",
        "symbol_b": "MSFT",
        "signal_type": "ENTER_LONG_SPREAD",
        "z_score": 1.2,
        "hedge_ratio": 0.8,
        "confidence": 0.85,
        "position_size": 1000,
        "shares_a": 100,
        "shares_b": -80,
        "volatility": 0.25,
        "correlation": 0.75
    })";
    
    SignalParser parser;
    RiskChecker checker;
    
    // Parse signal
    auto signal = parser.parseTradeSignal(testSignalJson);
    assertEqual(signal.pairName, "AAPL_MSFT", "Integration: signal parsing");
    
    // Check risk
    assertTrue(checker.checkSignalRisk(signal), "Integration: risk check");
    
    // Test position tracking
    PositionTracker tracker;
    tracker.updatePosition("AAPL", "BUY", signal.sharesA, 150.0);
    tracker.updatePosition("MSFT", "SELL", abs(signal.sharesB), 300.0);
    
    auto positions = tracker.getAllPositions();
    assertEqual(positions["AAPL"], 100.0, "Integration: AAPL position");
    assertEqual(positions["MSFT"], -80.0, "Integration: MSFT position");
    
    std::cout << "All integration tests passed!" << std::endl;
}

int main() {
    std::cout << "Starting C++ Trading System Unit Tests" << std::endl;
    
    try {
        testJsonParser();
        testSignalParser();
        testPositionTracker();
        testRiskChecker();
        testIntegration();
        
        std::cout << "\nALL TESTS PASSED!" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cerr << "Test failed with exception: " << e.what() << std::endl;
        return 1;
    }
} 