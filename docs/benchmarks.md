# Performance Benchmarks

## Test Environment

| Component | Spec |
|-----------|------|
| GPU | NVIDIA RTX 2060 6 GB |
| CUDA Toolkit | 12.1 (nvcc V12.1.66) |
| Driver | 535.x |
| OS | Windows 10 |
| Python | 3.10.11 |
| PyTorch | 2.1.0+cu121 |
| xformers | 0.0.22.post7 |
| TensorRT | 9.0.1.post11.dev4 |

All tests: 512×512, `use_tiny_vae=True`, `use_denoising_batch=True`, `warmup=10`, n=50 frames.

> **FPS variance note:** Measured range across multiple runs: **4.1–4.8 fps** (xformers, 2-step).
> The lower end (4.1) occurs when the GPU is thermally saturated or background processes are active.
> The upper end (~4.8) is the cold-start / idle-system result. Both are valid; quote the range.

---

## SD-Turbo — img2img

| Acceleration | Steps | t_index_list | FPS | Latency | VRAM |
|---|---|---|---|---|---|
| xformers | 2 | [35, 45] | **4.1–4.8** | 210–241 ms | 2,495 MB |
| xformers | 3 | [22, 32, 45] | **3.1–3.6** | 277–319 ms | 2,496 MB |
| TensorRT | 2 | [35, 45] | **5.59** | 172 ms | ~4,500 MB |

TRT improvement over xformers: **+23%** on RTX 2060 (Turing). Larger gains expected on Ampere/Ada (RTX 3000/4000).

---

## Kohaku v2.1 — img2img (with LCM-LoRA)

| Acceleration | Steps | t_index_list | FPS | VRAM |
|---|---|---|---|---|
| xformers | 2 | [32, 45] | ~4.5 | 2,657 MB |
| xformers | 3 | [22, 32, 45] | ~3.4 | 2,649 MB |
| xformers | 4 | [17, 25, 35, 45] | ~2.7 | 2,649 MB |

---

## Paper vs Hardware Comparison

| GPU | Paper FPS (approx) | Observed | Ratio |
|-----|-------------------|----------|-------|
| RTX 4090 | 100+ fps | — | — |
| RTX 3090 | 60+ fps | — | — |
| RTX 2060 | — | **4.1–5.59 fps** (xformers 4.1–4.8, TRT 5.59) | baseline |

Paper benchmarks are on RTX 3090/4090 with Linux. RTX 2060 has:
- ~3-5x fewer tensor cores
- ~3x lower memory bandwidth (336 GB/s vs 1008 GB/s on 4090)
- Turing vs Ada Lovelace generation

---

## TRT Engine Compilation Time

| Hardware | Compile Time | Cache Location |
|---|---|---|
| RTX 2060 | ~53 seconds | `engines/sd-turbo--*/` |

Compilation is one-time per GPU per config. Subsequent runs load cached engines in ~3 seconds.

---

## Resolution Scaling

At 512×512: 4.1–4.8 fps xformers baseline (thermal/load dependent).

| Resolution | Expected FPS | Notes |
|---|---|---|
| 384×384 | ~6.0–6.5 fps | ~30% faster (fewer tokens in attention) |
| 512×512 | 4.1–4.8 fps | Recommended sweet spot |
| 768×768 | ~2.0 fps | Quadratic attention scaling; approaches 6 GB VRAM limit |

768×768 is feasible for static generation but too slow for real-time on 6 GB.

---

## Reproducing Benchmarks

```powershell
# xformers benchmark
python scripts/research_benchmark.py --quick

# TensorRT benchmark (first run compiles engines ~53s)
python scripts/run_tensorrt_benchmark.py
```

Results are saved to `reports/benchmark_<timestamp>.md`.
