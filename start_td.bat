@echo off
title StreamDiffusion - TouchDesigner Bridge
cd /d "%~dp0"

echo ================================================================
echo  StreamDiffusion - TouchDesigner Bridge
echo  RTX 2060 ^| SD-Turbo ^| OSC ports 9000 / 9001
echo ================================================================
echo.
echo Select mode:
echo   1. SD-Turbo xformers  (~4.7 fps, starts in ~10s)
echo   2. SD-Turbo TensorRT  (~5.8 fps, ~53s compile first run)
echo   3. Kohaku quality     (~3.4 fps, better artistic output)
echo   4. Art installation   (consciousness projection preset)
echo.
set /p CHOICE="Enter 1-4 [default 1]: "
if "%CHOICE%"=="" set CHOICE=1

echo.
echo Select webcam index (usually 0 for built-in, 1 for USB):
set /p CAM="Webcam index [default 0]: "
if "%CAM%"=="" set CAM=0

echo.
call .venv\Scripts\activate.bat

if "%CHOICE%"=="2" (
    echo Starting TensorRT mode...
    echo NOTE: First run compiles GPU kernels (~53s, looks frozen - wait!)
    python td_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam %CAM%
) else if "%CHOICE%"=="3" (
    echo Starting Kohaku quality mode...
    python td_bridge.py --config configs/kohaku_quality.yaml --webcam %CAM%
) else if "%CHOICE%"=="4" (
    echo Starting art installation preset...
    python td_bridge.py --config configs/consciousness_projection.yaml --webcam %CAM%
) else (
    echo Starting xformers mode...
    python td_bridge.py --config configs/sdturbo_fast.yaml --webcam %CAM%
)

echo.
echo Bridge stopped.
pause
