@echo off
if /i not "%~1"=="__run_in_new_cmd__" (
    start "YOLO Adjust" cmd /k ""%~f0" __run_in_new_cmd__"
    exit /b
)

setlocal
cd /d "%~dp0"

python -c "from PIL import Image" >nul 2>&1
if errorlevel 1 (
    echo Missing dependency: Pillow
    echo.
    echo Installing Pillow for the current Python...
    python -m pip install Pillow
    if errorlevel 1 (
        echo.
        echo Pillow install failed. Please check the error above.
        pause
        exit /b 1
    )
)

python yolo_adjust_app.py
if errorlevel 1 (
    echo.
    echo YOLO Adjust exited with an error.
    pause
)
