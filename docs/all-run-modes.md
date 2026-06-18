# All Ways to Run StreamDiffusion

Complete reference for every runnable mode. All commands assume:

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
```

Validate your environment first:

```powershell
python scripts/test_cuda.py
```

---

## Quick-pick table

| Goal | Command / File | FPS (RTX 2060) |
|---|---|---|
| Webcam to browser (fastest start) | `demo/realtime-img2img/main.py` | 4.7 |
| Webcam to browser (TensorRT) | same + `--acceleration tensorrt` | 5.8 |
| Text prompt to browser | `demo/realtime-txt2img/main.py` | 4.7 |
| Video file to browser | `demo/vid2vid/app.py` | 4.7 |
| Screen capture to window | `examples/screen/main.py` | 4.7 |
| Image file to image file | `examples/img2img/single.py` | one-shot |
| Image file to image file (batch) | `examples/img2img/multi.py` | batch |
| Text to image file | `examples/txt2img/single.py` | one-shot |
| Text to image stream (viewer) | `examples/optimal-performance/single.py` | 4.7 |
| TouchDesigner NDI bridge | `touchdesigner/td_ndi_bridge.py` | 4.7-5.8 |
| TouchDesigner PNG bridge | `touchdesigner/td_bridge.py` | 4.7-5.8 |
| Build your own .tox operator | `touchdesigner/build_component.py` | -- |
| Benchmark xformers | `scripts/research_benchmark.py` | measures |
| Benchmark TensorRT | `scripts/run_tensorrt_benchmark.py` | measures |
| Multi-config comparison | `scripts/research_benchmark.py` | measures |

---

## 1. Web demos (browser UI)

All open at `http://localhost:8080`. Press `Ctrl+C` to stop.

### 1a. Realtime img2img (webcam to styled output)

```powershell
cd demo/realtime-img2img
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080 --acceleration xformers
```

With TensorRT (~23% faster, ~53s compile on first run):
```powershell
python main.py --port 8080 --acceleration tensorrt
```

Switch to Kohaku model (better artistic quality, ~3.4 fps):
```powershell
python main.py --port 8080 --model_id_or_path KBlueLeaf/kohaku-v2.1 --acceleration xformers
```

Webcam feed on the left, diffused output on the right. Type a prompt and it
applies in real time.

---

### 1b. Realtime txt2img (prompt to image stream)

```powershell
cd demo/realtime-txt2img
python main.py --port 8080
```

No camera needed. Type a prompt, watch continuous generation.

---

### 1c. vid2vid (video file to styled video)

```powershell
cd demo/vid2vid
python app.py --port 8080
```

Upload any `.mp4` or `.gif` via the browser. StreamDiffusion processes it
frame by frame and streams the output back.

---

## 2. Headless examples (no browser)

Output images are written to `images/outputs/`.

### 2a. img2img -- single image

```powershell
python examples/img2img/single.py `
  --input images/inputs/input.png `
  --output images/outputs/output.png `
  --model_id_or_path "KBlueLeaf/kohaku-v2.1" `
  --prompt "detailed oil painting, warm light" `
  --acceleration xformers `
  --seed 42
```

| Flag | Default | Notes |
|---|---|---|
| `--input` | `images/inputs/input.png` | Source image path |
| `--output` | `images/outputs/output.png` | Where to save |
| `--model_id_or_path` | `KBlueLeaf/kohaku-v2.1` | HuggingFace ID or local path |
| `--prompt` | (see script) | Text description |
| `--acceleration` | `xformers` | `none` / `xformers` / `tensorrt` |
| `--width` / `--height` | `512` | Output resolution |
| `--seed` | `2` | Reproducibility |
| `--cfg_type` | `self` | `none` / `self` / `full` / `initialize` |
| `--guidance_scale` | `1.2` | 1.0-1.5 effective range |

---

### 2b. img2img -- batch (multiple outputs)

```powershell
python examples/img2img/multi.py `
  --input images/inputs/input.png `
  --output images/outputs/ `
  --prompt "watercolor painting, soft tones"
```

---

### 2c. txt2img -- single image (no input image)

```powershell
python examples/txt2img/single.py `
  --output images/outputs/output.png `
  --model_id_or_path "KBlueLeaf/kohaku-v2.1" `
  --prompt "a mountain at sunset, digital art" `
  --acceleration xformers `
  --seed 42
```

---

### 2d. txt2img -- continuous stream with viewer

```powershell
python examples/txt2img/multi.py `
  --prompt "neon cityscape, cyberpunk" `
  --model_id_or_path "KBlueLeaf/kohaku-v2.1"
```

Generates images continuously in a viewer window.

---

### 2e. Optimal performance -- txt2img with live viewer

Uses multiprocessing (separate generation + display processes) for maximum
throughput.

```powershell
python examples/optimal-performance/single.py `
  --prompt "vivid fantasy landscape" `
  --model_id_or_path "KBlueLeaf/kohaku-v2.1" `
  --acceleration tensorrt
```

Multi-stream version:
```powershell
python examples/optimal-performance/multi.py
```

---

### 2f. Screen capture to live diffusion window

Captures a screen region, runs StreamDiffusion on it, displays output in a
floating window. Works on any app visible on screen.

```powershell
python examples/screen/main.py `
  --prompt "oil painting, impressionist" `
  --monitor "{\"top\": 300, \"left\": 200, \"width\": 512, \"height\": 512}" `
  --acceleration xformers
```

---

## 3. TouchDesigner integration

### 3a. NDI bridge (recommended)

Sends output as a real NDI video source. Best quality and latency.
Requires NDI SDK: https://ndi.video/download-ndi-sdk/

```powershell
python touchdesigner/td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
python touchdesigner/td_ndi_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam 0
python touchdesigner/td_ndi_bridge.py --config configs/kohaku_quality.yaml --webcam 0
python touchdesigner/td_ndi_bridge.py --config configs/consciousness_projection.yaml --webcam 0
```

**In TouchDesigner 2023:**
- Add **NDI In TOP** -> Source Name: `StreamDiffusion`
- Add **OSC Out CHOP** -> `127.0.0.1:9000` (send control)
- Add **OSC In CHOP** -> `127.0.0.1:9001` (receive stats)

**Send control via OSC (port 9000):**
```python
op('oscout1').sendOSC('/prompt',   ['oil painting, warm sunset'])
op('oscout1').sendOSC('/strength', [0.75])
op('oscout1').sendOSC('/seed',     [42])
op('oscout1').sendOSC('/pause',    [1])   # 1=pause, 0=resume
```

---

### 3b. Build your own .tox (free, one-time setup)

Auto-builds a full Container COMP with UI: Start/Stop, prompt, strength, seed,
guidance scale, live FPS/VRAM readout.

1. Start the NDI bridge first (step 3a)
2. In TouchDesigner: `Tab` -> **Text DAT** -> paste contents of `touchdesigner/build_component.py` -> right-click -> **Run Script**
3. `StreamDiffusionTD` component appears
4. Setup page -> **Base Folder**: `D:\Github\StreamDiffusion` -> **Start Stream**
5. Right-click -> **Save Component As** -> `StreamDiffusionTD.tox`

---

### 3c. PNG bridge (no NDI required)

Writes each frame to `td_out/current_frame.png`. TouchDesigner polls it via
File In TOP. Higher latency than NDI but no extra installs needed.

```powershell
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

In TouchDesigner:
- **File In TOP** -> `D:/Github/StreamDiffusion/td_out/current_frame.png`, Cook: Every Frame, Always Active: On
- **OSC Out CHOP** -> `127.0.0.1:9000`
- **OSC In CHOP** -> `127.0.0.1:9001`

See section 3a above for OSC control details.

---

## 4. Configs reference

| Config | Model | Steps | FPS (RTX 2060) | VRAM | Use when |
|---|---|---|---|---|---|
| `configs/sdturbo_fast.yaml` | SD-Turbo | 2 | **4.74** | ~2.5 GB | Default, always works |
| `configs/sdturbo_tensorrt.yaml` | SD-Turbo | 2 | **5.83** | ~4.5 GB | Fastest; ~53s compile first run |
| `configs/kohaku_quality.yaml` | Kohaku v2.1 + LCM-LoRA | 3 | **~3.4** | ~2.7 GB | Better artistic quality |
| `configs/consciousness_projection.yaml` | SD-Turbo | 2 | **~4.5** | ~2.5 GB | Art/creative with 7 preset prompts |

---

## 5. Benchmarks

```powershell
# xformers -- measures real FPS, saves to reports/
python scripts/research_benchmark.py --quick

# TensorRT -- compiles engines (~53s first run), then benchmarks
python scripts/run_tensorrt_benchmark.py

# Full benchmark (all models, 2/3/4-step configs)
python scripts/research_benchmark.py
```

Results saved to `reports/benchmark_<timestamp>.md`.

**Measured on RTX 2060 6 GB, SD-Turbo, 512x512:**

| Acceleration | FPS | Latency | VRAM |
|---|---|---|---|
| xformers | 4.74 | 211 ms | 2,495 MB |
| TensorRT | 5.83 | 172 ms | ~4,500 MB |

See section 4 (Configs reference) above for per-config details.

---

## 6. Acceleration modes

| Mode | Flag | When to use |
|---|---|---|
| `none` | `--acceleration none` | Debug only |
| `xformers` | `--acceleration xformers` | Default -- works immediately, ~2.5 GB VRAM |
| `tensorrt` | `--acceleration tensorrt` | Fastest -- ~53s compile first run, cached after |

TensorRT engines cache in `engines/` and load in ~3s on subsequent runs.

---

## 7. Parameter reference

| Parameter | Effect | Recommended range |
|---|---|---|
| `t_index_list` | Denoising step positions (0-50) | `[35,45]` for 2-step, `[22,32,45]` for 3-step |
| `guidance_scale` | Prompt adherence | 1.0-1.2 (above 1.5 is usually too strong) |
| `cfg_type` | CFG strategy | `none` for turbo models, `self` for SD 1.5 |
| `strength` | How much input image is preserved | 0.5 = subtle, 0.9 = radical |
| `seed` | Starting noise value | Fix while tuning other params |
| `use_tiny_vae` | Fast TAESD decoder | Always True for real-time |
| `use_denoising_batch` | Batch pipeline (key speedup) | Always True |
| `similar_image_filter` | Skip near-identical frames | Useful for noisy webcam |
