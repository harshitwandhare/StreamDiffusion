@echo off
title StreamDiffusion - TensorRT
cd /d "%~dp0"

echo ================================================================
echo  TensorRT mode - SD-Turbo 2-step (FASTEST)
echo  FIRST RUN: engine compile takes ~53s (looks frozen - wait!)
echo  Cached in engines/ after first run, loads in ~3s next time
echo ================================================================
echo.
call .venv\Scripts\activate.bat

echo Checking GPU...
python -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')"

echo.
echo   1. Run benchmark (measures FPS, saves to reports/)
echo   2. Run single inference test
echo.
set /p CHOICE="Enter 1 or 2: "

if "%CHOICE%"=="1" (
    python run_tensorrt_benchmark.py
) else (
    python examples\img2img\single.py ^
        --model_id_or_path "stabilityai/sd-turbo" ^
        --prompt "vivid digital painting, dynamic lighting, cinematic" ^
        --width 512 --height 512 ^
        --acceleration tensorrt ^
        --use_lcm_lora false ^
        --seed 42
)

echo.
pause
