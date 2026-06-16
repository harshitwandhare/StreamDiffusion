"""
TensorRT benchmark for StreamDiffusion on RTX 2060.
First run: engine compilation takes ~5-10 min (looks frozen — just wait).
Subsequent runs use cached engines and start immediately.
"""
import os
import sys
import time
from datetime import datetime

import numpy as np
import PIL.Image
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import tensorrt_loader  # noqa: F401 — must be first, pre-loads DLLs

from utils.wrapper import StreamDiffusionWrapper

MODEL = r"D:\Github\StreamDiffusion\models\sd-turbo"
WIDTH, HEIGHT = 512, 512
ITERATIONS = 50
WARMUP = 10
T_INDEX = [35, 45]


def main():
    print(f"StreamDiffusion TensorRT Benchmark")
    print(f"Model: {MODEL}")
    print(f"Resolution: {WIDTH}x{HEIGHT}")
    print(f"t_index: {T_INDEX}")
    print(f"Iterations: {ITERATIONS} (warmup: {WARMUP})")
    print()
    print("NOTE: First run compiles TRT engines (~5-10 min). Subsequent runs are instant.")
    print("-" * 60)

    stream = StreamDiffusionWrapper(
        model_id_or_path=MODEL,
        t_index_list=T_INDEX,
        lora_dict=None,
        mode="img2img",
        frame_buffer_size=1,
        width=WIDTH,
        height=HEIGHT,
        warmup=WARMUP,
        acceleration="tensorrt",
        use_lcm_lora=False,
        use_tiny_vae=True,
        enable_similar_image_filter=False,
        use_denoising_batch=True,
        cfg_type="none",
        seed=42,
    )

    stream.prepare(
        prompt="a beautiful landscape, high quality, detailed",
        negative_prompt="",
        num_inference_steps=50,
        guidance_scale=1.0,
        delta=0.5,
    )

    # Use solid color test image — no network needed
    test_image = PIL.Image.new("RGB", (WIDTH, HEIGHT), color=(128, 64, 32))

    print("Warming up...")
    for _ in range(WARMUP):
        image_tensor = stream.preprocess_image(test_image)
        stream(image=image_tensor)

    print(f"Benchmarking {ITERATIONS} iterations...")
    results = []
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)

    for i in range(ITERATIONS):
        start.record()
        image_tensor = stream.preprocess_image(test_image)
        stream(image=image_tensor)
        end.record()
        torch.cuda.synchronize()
        ms = start.elapsed_time(end)
        results.append(ms)
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{ITERATIONS}] {ms:.1f}ms / {1000/ms:.2f} fps")

    arr = np.array(results)
    avg_ms = arr.mean()
    avg_fps = 1000 / avg_ms
    print()
    print("=" * 60)
    print(f"TensorRT Results (SD-Turbo, {WIDTH}x{HEIGHT}, {len(T_INDEX)}-step)")
    print(f"  Avg latency : {avg_ms:.1f} ms")
    print(f"  Avg FPS     : {avg_fps:.2f}")
    print(f"  Max FPS     : {1000/arr.min():.2f}")
    print(f"  Min FPS     : {1000/arr.max():.2f}")
    print(f"  Std FPS     : {(1000/arr).std():.2f}")
    print("=" * 60)

    # Save report
    os.makedirs("reports", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = f"reports/benchmark_tensorrt_{ts}.md"
    with open(report_path, "w") as f:
        f.write(f"# TensorRT Benchmark {ts}\n\n")
        f.write(f"- Model: SD-Turbo (local)\n")
        f.write(f"- Resolution: {WIDTH}x{HEIGHT}\n")
        f.write(f"- t_index: {T_INDEX} ({len(T_INDEX)}-step)\n")
        f.write(f"- Acceleration: TensorRT 9.0.1\n")
        f.write(f"- GPU: RTX 2060 6GB\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Avg FPS | **{avg_fps:.2f}** |\n")
        f.write(f"| Avg latency | {avg_ms:.1f} ms |\n")
        f.write(f"| Max FPS | {1000/arr.min():.2f} |\n")
        f.write(f"| Min FPS | {1000/arr.max():.2f} |\n")
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
