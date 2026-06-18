# Windows TensorRT Setup Guide

This guide covers the extra steps required to use TensorRT acceleration on Windows. Linux users can skip this — TRT works out of the box on Linux.

## Root Cause

`nvinfer_plugin.dll` in TensorRT 9.x links against `cublas64_11.dll` (the CUDA 11 ABI naming convention). The CUDA 12 toolkit ships only `cublas64_12.dll`. This causes:

```
ImportError: DLL load failed while importing tensorrt: The specified module could not be found.
```

Additionally, Python 3.8+ on Windows no longer searches `PATH` for DLLs — all CUDA library directories must be registered explicitly via `os.add_dll_directory()`, and the DLLs must be loaded in dependency order.

## Prerequisites

- Windows 10/11
- CUDA Toolkit 12.x (for `cudart64_12.dll`, `cufft64_11.dll`, `cublas64_12.dll`)
- Python 3.10 (recommended; 3.11+ has compatibility issues with StreamDiffusion's C extensions)

## Installation

### 1. Install StreamDiffusion with TensorRT support

```bash
python -m streamdiffusion.tools.install-tensorrt
```

### 2. Install the missing cuBLAS 11 compatibility DLL

```bash
pip install "nvidia-cublas-cu11==11.11.3.6" --no-deps
```

This provides `cublas64_11.dll` and `cublasLt64_11.dll` required by `nvinfer_plugin.dll`.

### 3. Pin CUDA Python bindings to match TRT 9.x

```bash
pip install "nvidia-cuda-nvrtc-cu12==12.1.105" --force-reinstall --no-deps
pip install "cuda-python==12.1.0" --force-reinstall --no-deps
```

> **Why:** `cuda-python 13.x` uses CUDA 13 symbols. TRT 9.0.1 was built against CUDA 12. Also, `nvidia-cuda-nvrtc-cu12 12.9.x` places DLLs in the package root; `12.1.105` places them in `bin/`, which is the path `tensorrt_loader.py` expects.

### 4. Pre-load DLLs before importing TensorRT

The included `tensorrt_loader.py` handles this automatically. It is imported automatically by StreamDiffusion's TensorRT utilities on Windows. No manual action required after the pip installs above.

If you import TensorRT directly in your own code, add this before the import:

```python
import tensorrt_loader  # Windows only — no-op on Linux/Mac
import tensorrt as trt
```

## Version Matrix

| Package | Required version | Notes |
|---------|-----------------|-------|
| `tensorrt` | `9.0.1.post11.dev4` | Install via `install-tensorrt` script |
| `nvidia-cublas-cu11` | `11.11.3.6` | **Extra install — not in base requirements** |
| `nvidia-cublas-cu12` | `12.1.3.1` | Installed by pip; provides cublas64_12.dll |
| `nvidia-cudnn-cu12` | `8.9.4.25` | cuDNN 9.x dropped cudnn64_8.dll; must be 8.x |
| `nvidia-cuda-nvrtc-cu12` | `12.1.105` | 12.9.x has wrong DLL paths |
| `cuda-python` | `12.1.0` | Must match CUDA 12, not 13 |
| `numpy` | `<2` | PyTorch 2.1.0 requires numpy 1.x API |

## DLL Load Order

`tensorrt_loader.py` loads the following DLLs in this order. Each depends on those above it:

```
cudart64_12.dll              (CUDA runtime — from toolkit)
nvrtc-builtins64_121.dll     (NVRTC builtins — from pip cuda_nvrtc/bin/)
nvrtc64_120_0.dll            (NVRTC — from pip cuda_nvrtc/bin/)
cufft64_11.dll               (cuFFT — from toolkit)
cublas64_12.dll              (cuBLAS 12 — from toolkit)
cublasLt64_12.dll            (cuBLAS LT 12 — from toolkit)
cudnn64_8.dll                (cuDNN 8 — from pip cudnn/bin/)
nvinfer.dll                  (TensorRT core)
nvinfer_builder_resource.dll (TensorRT builder)
nvinfer_plugin.dll           (TensorRT plugins — needs cublas64_11.dll)
nvonnxparser.dll             (ONNX parser)
```

## Verifying the Fix

```bash
python -c "import tensorrt_loader; import tensorrt as trt; print('TRT', trt.__version__)"
# Expected: TRT 9.0.1.post11.dev4
```

## Performance (RTX 2060, SD-Turbo, 512x512)

| Acceleration | FPS | Latency | First-run compile |
|---|---|---|---|
| xformers | 4.1–4.8 | 241 ms | None |
| TensorRT | 5.59 | 172 ms | ~53 seconds |

TRT engine files are cached in `engines/` after the first run. Subsequent runs load in ~3 seconds.

> **Note:** TRT's gains are larger on Ampere/Ada GPUs (RTX 3000/4000 series). On Turing (RTX 2060), the improvement is ~23% due to limited sparse tensor core support.

## Troubleshooting

**`DLL load failed while importing tensorrt`**
→ Run `pip install "nvidia-cublas-cu11==11.11.3.6" --no-deps` and retry.

**`Could not find module '...nvrtc64_120_0.dll'`**
→ Run `pip install "nvidia-cuda-nvrtc-cu12==12.1.105" --force-reinstall --no-deps`.

**`cudnn64_8.dll not found`**
→ Ensure `nvidia-cudnn-cu12==8.9.4.25` is installed (not 9.x). Check `pip show nvidia-cudnn-cu12`.

**Engine compile looks frozen (5-10 minutes)**
→ Normal on first run. TRT is profiling kernels. Check Task Manager — python.exe should show 20-40% GPU. After compile, engines are cached and load in seconds.

**CUDA out of memory during compile**
→ TRT compilation peaks at ~4.5 GB VRAM. Close other GPU applications before running.
