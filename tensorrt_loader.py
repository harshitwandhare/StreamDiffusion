"""
Pre-load TensorRT DLLs on Windows in the correct dependency order.

Import this BEFORE importing tensorrt or any StreamDiffusion TRT acceleration.
Root cause: TensorRT 9.0.1 on Windows requires manual DLL loading because:
  1. Python 3.8+ no longer searches system PATH for DLLs (os.add_dll_directory required)
  2. nvinfer_plugin.dll links against cublas64_11.dll (CUDA 11 ABI), not cublas64_12.dll
  3. Exact load order matters for the dependency chain

Install once: pip install nvidia-cublas-cu11==11.11.3.6 --no-deps
"""
import ctypes
import os
import sys

def _load_trt_dlls():
    if sys.platform != "win32":
        return

    sp = None
    for path in sys.path:
        candidate = os.path.join(path, "nvidia")
        if os.path.isdir(candidate):
            sp = path
            break
    if sp is None:
        import site
        sp = site.getsitepackages()[0]

    cuda_bin = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin"

    dll_dirs = [
        cuda_bin,
        os.path.join(sp, "nvidia", "cuda_nvrtc", "bin"),
        os.path.join(sp, "nvidia", "cuda_runtime", "bin"),
        os.path.join(sp, "nvidia", "cublas", "bin"),
        os.path.join(sp, "nvidia", "cudnn", "bin"),
        os.path.join(sp, "tensorrt_libs"),
    ]
    for d in dll_dirs:
        if os.path.isdir(d):
            os.add_dll_directory(d)

    load_order = [
        (cuda_bin, "cudart64_12.dll"),
        (os.path.join(sp, "nvidia", "cuda_nvrtc", "bin"), "nvrtc-builtins64_121.dll"),
        (os.path.join(sp, "nvidia", "cuda_nvrtc", "bin"), "nvrtc64_120_0.dll"),
        (cuda_bin, "cufft64_11.dll"),
        (cuda_bin, "cublas64_12.dll"),
        (cuda_bin, "cublasLt64_12.dll"),
        (os.path.join(sp, "nvidia", "cudnn", "bin"), "cudnn64_8.dll"),
        (os.path.join(sp, "tensorrt_libs"), "nvinfer.dll"),
        (os.path.join(sp, "tensorrt_libs"), "nvinfer_builder_resource.dll"),
        (os.path.join(sp, "tensorrt_libs"), "nvinfer_plugin.dll"),
        (os.path.join(sp, "tensorrt_libs"), "nvonnxparser.dll"),
    ]
    for directory, dll in load_order:
        path = os.path.join(directory, dll)
        if os.path.exists(path):
            try:
                ctypes.CDLL(path)
            except OSError:
                pass


_load_trt_dlls()
