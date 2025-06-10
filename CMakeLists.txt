cmake_minimum_required(VERSION 3.10)
project(TWSConnect)

set(CMAKE_CXX_STANDARD 17)

include_directories("C:/TWSAPI/source/CppClient/client")

# set TWS API source directory
set(TWSAPI_SRC_DIR "C:/TWSAPI/source/CppClient/client")

# add all .cpp files in the TWS API source directory
file(GLOB TWSAPI_SOURCES "${TWSAPI_SRC_DIR}/*.cpp")

# include TWS API headers
include_directories(${TWSAPI_SRC_DIR})

add_executable(TWSConnect
    main.cpp
    MyWrapper.h
    ${TWSAPI_SOURCES}
)