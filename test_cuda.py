"""Quick sanity check — run this first to confirm the environment is good."""
import sys
import torch

print(f"Python: {sys.version}")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM: {vram:.1f} GB")
else:
    print("ERROR: CUDA not available. Check your driver and PyTorch install.")
    sys.exit(1)

try:
    import streamdiffusion
    print("streamdiffusion: OK")
except ImportError as e:
    print(f"streamdiffusion import failed: {e}")
    sys.exit(1)

try:
    import xformers
    print(f"xformers: {xformers.__version__}")
except ImportError:
    print("xformers: not installed")

print("\nAll good. Ready to run StreamDiffusion.")
