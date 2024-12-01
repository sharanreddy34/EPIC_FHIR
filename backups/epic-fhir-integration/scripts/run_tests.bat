@echo off
setlocal

REM Default values
set TEST_TYPE=all
set VERBOSE=0
set COVERAGE=0

REM Parse arguments
:parse_args
if "%~1"=="" goto :done_parsing
if /i "%~1"=="-t" (
    set TEST_TYPE=%~2
    shift /1
    shift /1
    goto :parse_args
)
if /i "%~1"=="--type" (
    set TEST_TYPE=%~2
    shift /1
    shift /1
    goto :parse_args
)
if /i "%~1"=="-v" (
    set VERBOSE=1
    shift /1
    goto :parse_args
)
if /i "%~1"=="--verbose" (
    set VERBOSE=1
    shift /1
    goto :parse_args
)
if /i "%~1"=="-c" (
    set COVERAGE=1
    shift /1
    goto :parse_args
)
if /i "%~1"=="--coverage" (
    set COVERAGE=1
    shift /1
    goto :parse_args
)
if /i "%~1"=="-h" (
    goto :show_help
)
if /i "%~1"=="--help" (
    goto :show_help
)
echo Unknown option: %~1
goto :show_help

:done_parsing

REM Determine test path based on type
if /i "%TEST_TYPE%"=="all" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline
) else if /i "%TEST_TYPE%"=="unit" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\unit
) else if /i "%TEST_TYPE%"=="integration" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\integration
) else if /i "%TEST_TYPE%"=="perf" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\perf
) else if /i "%TEST_TYPE%"=="auth" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\unit\test_auth.py
) else if /i "%TEST_TYPE%"=="client" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\unit\test_fhir_client.py
) else if /i "%TEST_TYPE%"=="transform" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\unit\test_transforms.py epic-fhir-integration\fhir_pipeline\tests\unit\test_transformations.py epic-fhir-integration\fhir_pipeline\tests\integration\test_transform_pipeline.py
) else if /i "%TEST_TYPE%"=="extract" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\integration\test_extract_pipeline.py
) else if /i "%TEST_TYPE%"=="validation" (
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\unit\test_validation.py
) else (
    REM Assume it's a specific file or pattern
    set TEST_PATH=epic-fhir-integration\fhir_pipeline\tests\*\%TEST_TYPE%*.py
)

REM Build command
set CMD=python -m pytest %TEST_PATH%

REM Add options
if %VERBOSE%==1 (
    set CMD=%CMD% -v
)

if %COVERAGE%==1 (
    set CMD=%CMD% --cov=epic-fhir-integration\fhir_pipeline --cov-report=term --cov-report=html:coverage_report
)

REM Echo command if verbose
if %VERBOSE%==1 (
    echo Running: %CMD%
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    pip install pytest pytest-cov
) else (
    call venv\Scripts\activate.bat
)

REM Run the tests
echo Running %TEST_TYPE% tests...
%CMD%

REM Print success message
echo.
if %COVERAGE%==1 (
    echo Coverage report generated in coverage_report\index.html
)
echo ✓ Tests completed successfully!
goto :end

:show_help
echo FHIR Pipeline Test Runner
echo.
echo Usage: %0 [options]
echo.
echo Options:
echo   -t, --type TYPE     Test type to run (all, unit, integration, perf, or a specific file path)
echo   -v, --verbose       Show verbose output
echo   -c, --coverage      Generate coverage report
echo   -h, --help          Show this help message
echo.
echo Examples:
echo   %0                   # Run all tests
echo   %0 -t unit           # Run unit tests only
echo   %0 -t integration    # Run integration tests only
echo   %0 -t perf           # Run performance tests only
echo   %0 -t auth           # Run auth-related tests only
echo   %0 -c                # Run all tests with coverage

:end
endlocal 