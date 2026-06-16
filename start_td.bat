@echo off
title StreamDiffusion - TouchDesigner Bridge (PNG)
cd /d "%~dp0"

echo ================================================================
echo  StreamDiffusion TouchDesigner Bridge (PNG fallback)
echo  In TouchDesigner: File In TOP -^> td_out/current_frame.png
echo  OSC control: port 9000   stats: port 9001
echo ================================================================
echo.
echo Select mode:
echo   1. SD-Turbo xformers  (~4.7 fps, starts in ~10s)  [default]
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
    echo Starting TensorRT mode...
    python touchdesigner/td_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam %CAM%
) else if "%CHOICE%"=="3" (
    python touchdesigner/td_bridge.py --config configs/kohaku_quality.yaml --webcam %CAM%
) else if "%CHOICE%"=="4" (
    python touchdesigner/td_bridge.py --config configs/consciousness_projection.yaml --webcam %CAM%
) else (
    python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam %CAM%
)

echo.
echo Bridge stopped.
pause
