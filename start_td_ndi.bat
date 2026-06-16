@echo off
title StreamDiffusion - NDI Bridge for TouchDesigner
cd /d "%~dp0"

echo ================================================================
echo  StreamDiffusion NDI Bridge
echo  Output appears as "StreamDiffusion" NDI source in TouchDesigner
echo  Add: NDI In TOP -^> select "StreamDiffusion"
echo ================================================================
echo.
echo Select mode:
echo   1. SD-Turbo xformers  (~4.7 fps)  [default]
echo   2. SD-Turbo TensorRT  (~5.8 fps, ~53s compile first run)
echo   3. Kohaku quality     (~3.4 fps)
echo   4. Art installation   (consciousness projection)
echo.
set /p CHOICE="Enter 1-4 [default 1]: "
if "%CHOICE%"=="" set CHOICE=1

echo.
set /p CAM="Webcam index [default 0]: "
if "%CAM%"=="" set CAM=0

echo.
call .venv\Scripts\activate.bat

if "%CHOICE%"=="2" (
    echo Starting TensorRT + NDI...
    echo NOTE: First run compiles ~53s, looks frozen - just wait.
    python touchdesigner/td_ndi_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam %CAM%
) else if "%CHOICE%"=="3" (
    echo Starting Kohaku + NDI...
    python touchdesigner/td_ndi_bridge.py --config configs/kohaku_quality.yaml --webcam %CAM%
) else if "%CHOICE%"=="4" (
    echo Starting art preset + NDI...
    python touchdesigner/td_ndi_bridge.py --config configs/consciousness_projection.yaml --webcam %CAM%
) else (
    echo Starting xformers + NDI...
    python touchdesigner/td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam %CAM%
)

echo.
echo Bridge stopped.
pause
