cmake_minimum_required(VERSION 3.10)
set(CMAKE_TOOLCHAIN_FILE "C:/Users/djray/Desktop/vcpkg/vcpkg/scripts/buildsystems/vcpkg.cmake")
project(TWSConnect)

set(CMAKE_CXX_STANDARD 17)

# Find required packages using vcpkg
find_package(ZeroMQ CONFIG REQUIRED)

# TWS API setup - assuming its installed onto the C drive... you may need to change this if you have it installed elsewhere
include_directories("C:/TWSAPI/source/CppClient/client")
set(TWSAPI_SRC_DIR "C:/TWSAPI/source/CppClient/client")
file(GLOB TWSAPI_SOURCES "${TWSAPI_SRC_DIR}/*.cpp")
include_directories(${TWSAPI_SRC_DIR})

# Include directories
include_directories(include)

# Source files
set(SOURCES
    src/main.cpp
    src/tws_integration/MyWrapper.cpp
    src/tws_integration/OrderUtils.cpp
    src/comms/signal_parser.cpp
    src/comms/signal_watcher.cpp
    src/order_exec/order_manager.cpp
    src/order_exec/position_tracker.cpp
    src/order_exec/risk_checker.cpp
    ${TWSAPI_SOURCES}
)

# Create executable
add_executable(TWSConnect ${SOURCES})

# Link libraries
target_link_libraries(TWSConnect PRIVATE libzmq)

# Test targets
enable_testing()

# Unit tests
add_executable(unit_tests
    tests/unit_tests.cpp
    src/comms/signal_parser.cpp
    src/order_exec/position_tracker.cpp
    src/order_exec/risk_checker.cpp
    ${TWSAPI_SOURCES}
)

target_link_libraries(unit_tests PRIVATE libzmq)

# Integration tests
add_executable(integration_tests
    tests/integration_test.cpp
    src/comms/signal_parser.cpp
    src/comms/signal_watcher.cpp
    src/order_exec/position_tracker.cpp
    src/order_exec/risk_checker.cpp
    ${TWSAPI_SOURCES}
)

target_link_libraries(integration_tests PRIVATE libzmq)

# Add tests
add_test(NAME UnitTests COMMAND unit_tests)
add_test(NAME IntegrationTests COMMAND integration_tests)

# ZeroMQ test
add_executable(test_zeromq test_zeromq.cpp)
target_link_libraries(test_zeromq PRIVATE libzmq)
add_test(NAME ZeroMQTest COMMAND test_zeromq)

# Latency measurement test
add_executable(latency_measurement_test 
    tests/latency_measurement_test.cpp
    src/order_exec/position_tracker.cpp
    src/order_exec/risk_checker.cpp
)
target_link_libraries(latency_measurement_test PRIVATE libzmq)