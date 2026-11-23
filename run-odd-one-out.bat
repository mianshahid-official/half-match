@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   Odd One Out - Kids Video Generator
echo ===================================================
echo.

:: 1. Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found on your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo and ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check if FFmpeg is installed
where ffmpeg >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] FFmpeg is missing from your system PATH!
    echo FFmpeg is required to render and encode the videos.
    echo.
    echo To install FFmpeg on Windows:
    echo   winget install Gyan.FFmpeg
    echo or download from https://www.gyan.dev/ffmpeg/builds/
    echo and add the bin folder to your System PATH.
    echo.
    pause
    exit /b 1
)

:: 3. Check / install dependencies if missing
python -c "import PIL, numpy" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing required dependencies (Pillow, numpy)...
    python -m pip install pillow numpy
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: 4. Prompt for settings if run interactively (no arguments provided)
set "ROUNDS_ARG="
set "WAIT_ARG="

if "%~1"=="" (
    echo ---------------------------------------------------
    echo Video Settings (Press Enter to use defaults)
    echo ---------------------------------------------------
    set /p "INPUT_ROUNDS=Number of rounds [default: 5]: "
    set /p "INPUT_WAIT=Wait time before reveal in seconds [default: 5.0]: "
    echo.
)

if not "%INPUT_ROUNDS%"=="" (
    set ROUNDS_ARG=--rounds %INPUT_ROUNDS%
)
if not "%INPUT_WAIT%"=="" (
    set WAIT_ARG=--wait-time %INPUT_WAIT%
)

:: 5. Run odd_one_out.py
echo Starting Odd One Out video generation...
echo.
python odd_one_out.py %ROUNDS_ARG% %WAIT_ARG% %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Video generation failed with exit code: %ERRORLEVEL%
) else (
    echo.
    echo [SUCCESS] Generation complete!
)

echo.
pause
