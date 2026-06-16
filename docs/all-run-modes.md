# All Ways to Run StreamDiffusion

Complete reference for every runnable mode. All commands assume you are in
`D:\Github\StreamDiffusion` with the venv active:

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
```

Run `python test_cuda.py` first to validate your environment.

---

## Quick-pick table

| Goal | Command / File | FPS (RTX 2060) |
|---|---|---|
| Webcam → browser (fastest start) | `demo/realtime-img2img/main.py` | 4.7 |
| Webcam → browser (TensorRT) | same + `--acceleration tensorrt` | 5.8 |
| Text prompt → browser | `demo/realtime-txt2img/main.py` | 4.7 |
| Video file → browser | `demo/vid2vid/app.py` | 4.7 |
| Screen capture → window | `examples/screen/main.py` | 4.7 |
| Image file → image file | `examples/img2img/single.py` | one-shot |
| Image file → image file (batch) | `examples/img2img/multi.py` | batch |
| Text → image file | `examples/txt2img/single.py` | one-shot |
| Text → image stream (viewer) | `examples/optimal-performance/single.py` | 4.7 |
| TouchDesigner (NDI, one-click) | `start_td_ndi.bat` | 4.7–5.8 |
| TouchDesigner (PNG fallback) | `start_td.bat` | 4.7–5.8 |
| Build your own .tox operator | `touchdesigner/build_component.py` | — |
| Benchmark xformers | `research_benchmark.py` | measures |
| Benchmark TensorRT | `run_tensorrt_benchmark.py` | measures |
| Multi-config comparison | `demo_tier2.py` | measures |

---

## 1. Web demos (browser UI)

All web demos open at `http://localhost:8080`. Press `Ctrl+C` to stop.

### 1a. Realtime img2img (webcam → styled output)

```powershell
cd demo/realtime-img2img
python main.py --port 8080 --acceleration xformers
```

With TensorRT (~23% faster, ~53s compile on first run):
```powershell
python main.py --port 8080 --acceleration tensorrt
```

Use a local model (skip HuggingFace download):
```powershell
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080
```

**What you get:** webcam feed on the left, diffused output on the right. Type a
prompt in the text box. Output updates every frame in real time.

---

### 1b. Realtime txt2img (prompt → image stream)

```powershell
cd demo/realtime-txt2img
python main.py --port 8080
```

No camera needed. Type a prompt, watch continuous image generation.

---

### 1c. vid2vid (video file → styled video)

```powershell
cd demo/vid2vid
python app.py --port 8080
```

Upload any `.mp4` or `.gif` via the browser UI. StreamDiffusion processes it
frame by frame and streams the output back.

---

## 2. Headless examples (no browser)

These run in the terminal and write output images to `images/outputs/`.

### 2a. img2img — single image

```powershell
python examples/img2img/single.py `
  --input images/inputs/input.png `
  --output images/outputs/output.png `
  --model_id_or_path "KBlueLeaf/kohaku-v2.1" `
  --prompt "detailed oil painting, warm light" `
  --acceleration xformers `
  --seed 42
```

Key flags:
| Flag | Default | Notes |
|---|---|---|
| `--input` | `images/inputs/input.png` | Path to source image |
| `--output` | `images/outputs/output.png` | Where to save result |
| `--model_id_or_path` | `KBlueLeaf/kohaku-v2.1` | HuggingFace ID or local path |
| `--prompt` | (see script) | Text description |
| `--acceleration` | `xformers` | `none` / `xformers` / `tensorrt` |
| `--width` / `--height` | `512` | Output resolution |
| `--seed` | `2` | Reproducibility |
| `--cfg_type` | `self` | `none` / `self` / `full` / `initialize` |
| `--guidance_scale` | `1.2` | 1.0–1.5 effective range |

---

### 2b. img2img — batch (multiple outputs)

```powershell
python examples/img2img/multi.py `
  --input images/inputs/input.png `
  --output images/outputs/ `
  --prompt "watercolor painting, soft tones"
```

Runs the denoising batch pipeline (frame buffer mode) — same technique used
in real-time mode. Outputs a sequence of images.

---

### 2c. txt2img — single image (no input image)

```powershell
python examples/txt2img/single.py `
  --output images/outputs/output.png `
  --model_id_or_path "KBlueLeaf/kohaku-v2.1" `
  --prompt "a mountain at sunset, digital art" `
  --acceleration xformers `
  --seed 42
```

---

### 2d. txt2img — batch stream

```powershell
python examples/txt2img/multi.py `
  --prompt "neon cityscape, cyberpunk" `
  --model_id_or_path "KBlueLeaf/kohaku-v2.1"
```

Generates images continuously in a viewer window.

---

### 2e. Optimal performance — txt2img with viewer window

```powershell
python examples/optimal-performance/single.py `
  --prompt "vivid fantasy landscape" `
  --model_id_or_path "KBlueLeaf/kohaku-v2.1" `
  --acceleration tensorrt
```

Opens a Tkinter window showing continuous generation at maximum speed.
Uses multiprocessing (separate generation + display processes).

Multi-stream version:
```powershell
python examples/optimal-performance/multi.py
```

---

### 2f. Screen capture → live diffusion window

Captures a region of your screen, runs it through StreamDiffusion, displays
the output in a floating window. Useful for creative effects on any app.

```powershell
python examples/screen/main.py `
  --prompt "oil painting, impressionist" `
  --monitor '{"top": 300, "left": 200, "width": 512, "height": 512}' `
  --acceleration xformers
```

Move/resize the capture region with the Tkinter window that appears.

---

## 3. TouchDesigner integration

Three ways — pick based on your setup.

### 3a. NDI bridge (recommended)

Sends output as a proper NDI video source. No PNG polling. Best quality and
lowest latency. NDI SDK must be installed from https://ndi.video/download-ndi-sdk/

**One-click:**
```
Double-click start_td_ndi.bat
→ pick mode (1–4) and webcam index
→ wait for "[ready] StreamDiffusion active"
```

**Or directly:**
```powershell
python td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
python td_ndi_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam 0
python td_ndi_bridge.py --config configs/kohaku_quality.yaml --webcam 0
python td_ndi_bridge.py --config configs/consciousness_projection.yaml --webcam 0
```

**In TouchDesigner:**
- Add **NDI In TOP** → Source Name: `StreamDiffusion`
- Add **OSC Out CHOP** → `127.0.0.1:9000` (send control)
- Add **OSC In CHOP** → `127.0.0.1:9001` (receive stats)

**OSC control (send to port 9000):**
```python
op('oscout1').sendOSC('/prompt',   ['oil painting, warm sunset'])
op('oscout1').sendOSC('/strength', [0.75])
op('oscout1').sendOSC('/seed',     [42])
op('oscout1').sendOSC('/pause',    [1])   # 1 = pause, 0 = resume
```

---

### 3b. Build your own .tox operator (free, one-time)

Creates a self-contained Container COMP with full UI — Start/Stop buttons,
prompt, strength, seed, guidance scale, live FPS/VRAM display.

1. Start `td_ndi_bridge.py` (step 3a above)
2. In TouchDesigner: `Tab` → **Text DAT** → paste contents of
   `touchdesigner/build_component.py` → right-click → **Run Script**
3. `StreamDiffusionTD` component appears in your network
4. Setup page → set **Base Folder** to `D:\Github\StreamDiffusion` → **▶ Start Stream**
5. Right-click component → **Save Component As** → `StreamDiffusionTD.tox`

Full instructions: [`touchdesigner/HOW_TO_BUILD_TOX.md`](../touchdesigner/HOW_TO_BUILD_TOX.md)

---

### 3c. PNG bridge (no NDI required)

Simpler fallback. Writes each frame to `td_out/current_frame.png`.
TouchDesigner polls the file with a File In TOP. Higher latency than NDI.

**One-click:**
```
Double-click start_td.bat
```

**Or directly:**
```powershell
python td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

**In TouchDesigner:**
- Add **File In TOP** → path: `D:/Github/StreamDiffusion/td_out/current_frame.png`,
  Cook: Every Frame, Always Active: On
- Add **OSC Out CHOP** → `127.0.0.1:9000`
- Add **OSC In CHOP** → `127.0.0.1:9001`

---

## 4. Configs (all TD bridge modes)

| Config file | Model | Steps | FPS (RTX 2060) | Use when |
|---|---|---|---|---|
| `configs/sdturbo_fast.yaml` | SD-Turbo | 2 | **4.74** | Default, always works, ~2.5 GB VRAM |
| `configs/sdturbo_tensorrt.yaml` | SD-Turbo | 2 | **5.83** | Fastest; ~53s compile first run, ~4.5 GB VRAM |
| `configs/kohaku_quality.yaml` | Kohaku v2.1 + LCM-LoRA | 3 | **~3.4** | Better artistic quality |
| `configs/consciousness_projection.yaml` | SD-Turbo | 2 | **~4.5** | Art/creative — 7 preset prompts |

---

## 5. Benchmarks

```powershell
# xformers — measures real FPS on your GPU, saves to reports/
python research_benchmark.py --quick

# TensorRT — first run compiles engines (~53s), then benchmarks
python run_tensorrt_benchmark.py

# Multi-config comparison (2-step / 3-step / 4-step)
python demo_tier2.py
```

Results are saved to `reports/benchmark_<timestamp>.md`.

**Measured results on RTX 2060 6 GB, SD-Turbo, 512×512:**

| Acceleration | FPS | Latency | VRAM |
|---|---|---|---|
| xformers | 4.74 | 211 ms | 2,495 MB |
| TensorRT | 5.83 | 172 ms | ~4,500 MB |

---

## 6. Environment check

```powershell
python test_cuda.py
```

Validates: CUDA availability, xformers, TensorRT import, model files present.
Run this first if anything seems broken.

---

## 7. Acceleration options explained

| Mode | How to use | When to use |
|---|---|---|
| `none` | `--acceleration none` | Debug only — no speed optimization |
| `xformers` | `--acceleration xformers` | Default. Works immediately, ~2.5 GB VRAM |
| `tensorrt` | `--acceleration tensorrt` | Fastest. First run compiles ~53s, cached after |

TensorRT is only worth it if you'll run StreamDiffusion repeatedly. The compiled
engines live in `engines/` and load in ~3s on all subsequent runs.

---

## 8. Parameter reference

| Parameter | Effect | Good starting range |
|---|---|---|
| `t_index_list` | Denoising step positions (0–50) | `[35, 45]` for 2-step, `[22, 32, 45]` for 3-step |
| `guidance_scale` | Prompt adherence | 1.0–1.2 (above 1.5 is usually too strong) |
| `cfg_type` | CFG strategy | `none` for turbo models, `self` for others |
| `strength` (img2img) | How much input image is preserved | 0.5 = subtle, 0.9 = radical |
| `seed` | Starting noise | Fix while tuning other params |
| `use_tiny_vae` | Use fast TAESD decoder | Always True for real-time |
| `use_denoising_batch` | Batch pipeline (key speedup) | Always True |
| `similar_image_filter` | Skip near-identical frames | Useful for noisy webcam |
