@echo off
echo ========================================
echo C++ Trading System Test Runner
echo ========================================

REM Check if build directory exists
if not exist "build" (
    echo Creating build directory...
    mkdir build
)

cd build

REM Configure with CMake
echo Configuring with CMake...
cmake .. -DCMAKE_BUILD_TYPE=Release
if %ERRORLEVEL% neq 0 (
    echo CMake configuration failed!
    pause
    exit /b 1
)

REM Build the project
echo Building project...
cmake --build . --config Release
if %ERRORLEVEL% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Running Unit Tests
echo ========================================
if exist "unit_tests.exe" (
    unit_tests.exe
    if %ERRORLEVEL% neq 0 (
        echo Unit tests failed!
        pause
        exit /b 1
    )
) else (
    echo Unit tests executable not found!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Running Integration Tests
echo ========================================
if exist "integration_tests.exe" (
    integration_tests.exe
    if %ERRORLEVEL% neq 0 (
        echo Integration tests failed!
        pause
        exit /b 1
    )
) else (
    echo Integration tests executable not found!
    pause
    exit /b 1
)

echo.
echo ========================================
echo All Tests Completed Successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Configure TWS for paper trading
echo 2. Start Python data engine
echo 3. Run: .\TWSConnect.exe
echo.
pause 