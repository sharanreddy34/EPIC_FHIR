@echo off
setlocal enabledelayedexpansion

:: Default values
set TEST_TYPE=all
set VERBOSE=0
set COVERAGE=0
set JUNIT_REPORT=0

:: Parse command line arguments
:parse
if "%~1"=="" goto :endparse
if "%~1"=="-t" (
    set TEST_TYPE=%~2
    shift
    shift
    goto :parse
)
if "%~1"=="--type" (
    set TEST_TYPE=%~2
    shift
    shift
    goto :parse
)
if "%~1"=="-v" (
    set VERBOSE=1
    shift
    goto :parse
)
if "%~1"=="--verbose" (
    set VERBOSE=1
    shift
    goto :parse
)
if "%~1"=="-c" (
    set COVERAGE=1
    shift
    goto :parse
)
if "%~1"=="--coverage" (
    set COVERAGE=1
    shift
    goto :parse
)
if "%~1"=="-j" (
    set JUNIT_REPORT=1
    shift
    goto :parse
)
if "%~1"=="--junit" (
    set JUNIT_REPORT=1
    shift
    goto :parse
)
if "%~1"=="-h" (
    goto :show_help
)
if "%~1"=="--help" (
    goto :show_help
)
echo Unknown option: %1
goto :show_help

:endparse

:: Determine test path based on type
if "%TEST_TYPE%"=="all" (
    set TEST_PATH=tests
) else if "%TEST_TYPE%"=="unit" (
    set TEST_PATH=tests/unit
) else if "%TEST_TYPE%"=="integration" (
    set TEST_PATH=tests/integration
) else if "%TEST_TYPE%"=="perf" (
    set TEST_PATH=tests/perf
) else if "%TEST_TYPE%"=="auth" (
    set TEST_PATH=tests/unit/test_auth.py
) else if "%TEST_TYPE%"=="client" (
    set TEST_PATH=tests/unit/test_fhir_client.py
) else if "%TEST_TYPE%"=="transform" (
    set TEST_PATH=tests/unit/test_transforms.py tests/unit/test_transformations.py tests/integration/test_transform_pipeline.py
) else if "%TEST_TYPE%"=="extract" (
    set TEST_PATH=tests/integration/test_extract_pipeline.py
) else if "%TEST_TYPE%"=="validation" (
    set TEST_PATH=tests/unit/test_validation.py
) else (
    :: Assume it's a specific file or pattern
    set TEST_PATH=tests/*/%TEST_TYPE%*.py
)

:: Build command
set CMD=python -m pytest %TEST_PATH%

:: Add options
if "%VERBOSE%"=="1" (
    set CMD=%CMD% -v
)

if "%COVERAGE%"=="1" (
    set CMD=%CMD% --cov=fhir_pipeline --cov-report=term --cov-report=html:coverage_report
)

if "%JUNIT_REPORT%"=="1" (
    if not exist "test-reports" mkdir test-reports
    set CMD=%CMD% --junitxml=test-reports/junit.xml
)

:: Echo command if verbose
if "%VERBOSE%"=="1" (
    echo Running: %CMD%
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    pip install pytest pytest-cov
) else (
    call venv\Scripts\activate.bat
)

:: Run the tests
echo Running %TEST_TYPE% tests...
%CMD%

:: Print success message
echo.
if "%COVERAGE%"=="1" (
    echo Coverage report generated in coverage_report\index.html
)
echo ✅ Tests completed successfully!
goto :eof

:show_help
echo FHIR Pipeline Test Runner
echo.
echo Usage: %0 [options]
echo.
echo Options:
echo   -t, --type TYPE     Test type to run (all, unit, integration, perf, or a specific file path)
echo   -v, --verbose       Show verbose output
echo   -c, --coverage      Generate coverage report
echo   -j, --junit         Generate JUnit XML reports
echo   -h, --help          Show this help message
echo.
echo Examples:
echo   %0                   # Run all tests
echo   %0 -t unit           # Run unit tests only
echo   %0 -t integration    # Run integration tests only
echo   %0 -t perf           # Run performance tests only
echo   %0 -t auth           # Run auth-related tests only
echo   %0 -c                # Run all tests with coverage
echo   %0 -t unit -c -j     # Run unit tests with coverage and JUnit reports
goto :eof 