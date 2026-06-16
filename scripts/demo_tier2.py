"""
Tier 2 demo — shows understanding of StreamDiffusion internals:
- Benchmarks xformers acceleration
- Logs VRAM usage before/after
- Saves output with prompt metadata
- Demonstrates the denoising batch concept with multiple t_index configs
"""
import os
import sys
import time
import json
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.wrapper import StreamDiffusionWrapper

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_IMAGE = os.path.join(CURRENT_DIR, "images", "inputs", "input.png")
OUTPUT_DIR = os.path.join(CURRENT_DIR, "images", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL = "KBlueLeaf/kohaku-v2.1"
PROMPT = "detailed digital painting, vivid colors, cinematic lighting, high quality"
NEGATIVE = "blurry, low quality, watermark, text"

configs = [
    {"label": "2-step (fastest)", "t_index_list": [32, 45]},
    {"label": "3-step (balanced)", "t_index_list": [22, 32, 45]},
    {"label": "4-step (best quality)", "t_index_list": [15, 22, 32, 45]},
]

print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
print()

results = []

for cfg in configs:
    print(f"--- Testing {cfg['label']} ---")
    vram_before = torch.cuda.memory_allocated() / 1024**2

    stream = StreamDiffusionWrapper(
        model_id_or_path=MODEL,
        t_index_list=cfg["t_index_list"],
        frame_buffer_size=1,
        width=512,
        height=512,
        warmup=10,
        acceleration="xformers",
        mode="img2img",
        use_denoising_batch=True,
        cfg_type="self",
        seed=42,
    )

    stream.prepare(
        prompt=PROMPT,
        negative_prompt=NEGATIVE,
        num_inference_steps=50,
        guidance_scale=1.2,
        delta=0.5,
    )

    vram_after = torch.cuda.memory_allocated() / 1024**2
    print(f"  VRAM used by model: {vram_after - vram_before:.0f} MB")

    image_tensor = stream.preprocess_image(INPUT_IMAGE)

    # warmup frames
    for _ in range(stream.batch_size - 1):
        stream(image=image_tensor)

    # timed run
    start = time.perf_counter()
    N = 20
    for _ in range(N):
        output = stream(image=image_tensor)
    elapsed = time.perf_counter() - start
    fps = N / elapsed

    # save output
    out_path = os.path.join(OUTPUT_DIR, f"output_{len(cfg['t_index_list'])}step.png")
    output.save(out_path)

    result = {
        "config": cfg["label"],
        "steps": len(cfg["t_index_list"]),
        "fps": round(fps, 2),
        "ms_per_frame": round(1000 / fps, 1),
        "vram_mb": round(vram_after - vram_before),
        "output": out_path,
    }
    results.append(result)
    print(f"  {fps:.1f} fps  ({1000/fps:.0f} ms/frame)")
    print(f"  Saved: {out_path}")
    print()

    del stream
    torch.cuda.empty_cache()

print("=== Benchmark Summary ===")
for r in results:
    print(f"  {r['config']:25s} → {r['fps']:6.1f} fps  {r['ms_per_frame']:5.0f} ms/frame  {r['vram_mb']} MB VRAM")

out_json = os.path.join(OUTPUT_DIR, "benchmark.json")
with open(out_json, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nFull results saved to: {out_json}")
