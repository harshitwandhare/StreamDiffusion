# All Ways to Run StreamDiffusion

Complete reference for every runnable mode on Windows with RTX 2060.

All commands assume you are in the repo root with venv active:

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
```

Verify your environment first:

```powershell
python scripts/test_cuda.py
```

Expected: `GPU: NVIDIA GeForce RTX 2060`, `xformers: 0.0.22.post7`, `All good.`

---

## Quick-pick table

| Goal | Script | FPS (RTX 2060) | Status |
|---|---|---|---|
| Webcam to browser (fastest) | `demo/realtime-img2img/main.py` | 4.8 | WORKS |
| Text prompt to browser | `demo/realtime-txt2img/main.py` | — | BROKEN (upstream TS build error) |
| Video file to video file | `examples/vid2vid/main.py` | — | WORKS |
| Screen capture to window | `examples/screen/main.py` | 4.8 | WORKS |
| Image → image (single) | `examples/img2img/single.py` | one-shot | WORKS |
| Image → image (batch) | `examples/img2img/multi.py` | batch | WORKS |
| Text → image (single) | `examples/txt2img/single.py` | one-shot | WORKS (Kohaku only, not SD-Turbo) |
| TouchDesigner PNG bridge | `touchdesigner/td_bridge.py` | 4.8 | WORKS |
| TouchDesigner NDI bridge | `touchdesigner/td_ndi_bridge.py` | 4.8 | WORKS (needs NDI SDK) |
| Build .tox component | `touchdesigner/build_component.py` | — | Run inside TD |
| Benchmark xformers | `scripts/research_benchmark.py` | measures | WORKS |
| Benchmark TensorRT | `scripts/run_tensorrt_benchmark.py` | measures | WORKS |

---

## 1. Web demo — realtime img2img

Webcam on left, diffused output on right. Runs in browser.

```powershell
cd demo\realtime-img2img
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080 --acceleration xformers
```

Open **http://localhost:8080**. Type a prompt and watch the output update live (~4.8 fps).

Switch to Kohaku for better artistic quality (~3.4 fps):
```powershell
python main.py --port 8080 --model_id_or_path KBlueLeaf/kohaku-v2.1 --acceleration xformers
```

With TensorRT (~5.8 fps, ~53s compile on first run):
```powershell
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080 --acceleration tensorrt
```

Press `Ctrl+C` to stop. Return to repo root before running other scripts:
```powershell
cd D:\Github\StreamDiffusion
```

> **Note**: Must run from `demo\realtime-img2img\` directory — the server looks for `./frontend/public` relative to its own location.

---

## 2. Headless examples

Output images are written to `images/outputs/`.

### 2a. img2img — single image

```powershell
python examples/img2img/single.py `
  --model_id_or_path "D:\Github\StreamDiffusion\models\sd-turbo" `
  --prompt "vivid oil painting, golden hour, cinematic" `
  --acceleration xformers `
  --cfg_type none `
  --guidance_scale 1.0 `
  --seed 42
```

Output: `images/outputs/output.png`

| Flag | Default | Notes |
|---|---|---|
| `--input` | `images/inputs/input.png` | Source image path |
| `--output` | `images/outputs/output.png` | Where to save |
| `--model_id_or_path` | `KBlueLeaf/kohaku-v2.1` | HuggingFace ID or local path |
| `--cfg_type` | `self` | Use `none` for SD-Turbo, `self` for Kohaku |
| `--guidance_scale` | `1.2` | Set to `1.0` when using `cfg_type none` |
| `--acceleration` | `xformers` | `none` / `xformers` / `tensorrt` |

---

### 2b. img2img — batch (multiple outputs from one input)

```powershell
python examples/img2img/multi.py `
  --input images/inputs/input.png `
  --output images/outputs/ `
  --prompt "watercolor painting, soft tones" `
  --acceleration xformers
```

---

### 2c. txt2img — single image (no input required)

> **Important**: Use Kohaku model only. SD-Turbo in txt2img mode crashes due to batch size mismatch in the 4-step scheduler — this is an upstream limitation.

```powershell
python examples/txt2img/single.py `
  --prompt "a mountain at sunset, digital art, cinematic" `
  --acceleration xformers `
  --seed 42
```

Output: `images/outputs/output.png`

---

### 2d. Screen capture → live diffusion window

Captures a screen region and applies StreamDiffusion in real time. Output appears in a floating window.

```powershell
python examples/screen/main.py `
  --prompt "oil painting, impressionist style" `
  --acceleration xformers `
  --model_id_or_path "D:\Github\StreamDiffusion\models\sd-turbo"
```

Optional: specify screen region (JSON string, no spaces):
```powershell
--monitor "{`"top`":300,`"left`":200,`"width`":512,`"height`":512}"
```

---

### 2e. Video file → diffused video file

```powershell
python examples/vid2vid/main.py `
  path\to\input.mp4 `
  --output images/outputs/output.mp4 `
  --prompt "oil painting, warm tones" `
  --acceleration xformers
```

---

## 3. TouchDesigner integration

Full guide: [`docs/touchdesigner-setup.md`](touchdesigner-setup.md)

### 3a. PNG bridge (no extra installs — use this for demo)

**Step 1 — Start Python backend:**
```powershell
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

Wait for:
```
[INIT] Model ready.
[RUN] Streaming. Ctrl+C to stop.
      Input:  webcam 0
      Output: td_out/
```

Switch models by stopping (Ctrl+C) and re-running with a different config:
```powershell
python touchdesigner/td_bridge.py --config configs/kohaku_quality.yaml --webcam 0
python touchdesigner/td_bridge.py --config configs/consciousness_projection.yaml --webcam 0
python touchdesigner/td_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam 0
```

**Step 2 — TouchDesigner network setup:**

1. Open TouchDesigner 2023 → new empty project
2. Press `Tab` → search `File In` → place **File In TOP**
   - **File**: `D:/Github/StreamDiffusion/td_out/current_frame.png` (forward slashes)
   - **Cook**: `Every Frame`
   - **Always Active**: On
   - Live frames appear in the node viewer
3. Press `Tab` → search `OSC Out` → place **OSC Out CHOP**
   - **Network Address**: `127.0.0.1`
   - **Network Port**: `9000`
4. Press `Tab` → search `OSC In` → place **OSC In CHOP**
   - **Network Address**: `0.0.0.0`
   - **Network Port**: `9001`
   - You'll see `/fps`, `/vram_used`, `/status` channels appear

**Step 3 — Send OSC control from TouchDesigner:**

Add a **Text DAT** → paste this → right-click → **Run Script**:
```python
# Change prompt
op('oscout1').sendOSC('/prompt', ['abstract generative art, flowing light, ethereal'])

# Adjust transformation strength (0.0 = no change, 1.0 = full transform)
op('oscout1').sendOSC('/strength', [0.75])

# Change seed
op('oscout1').sendOSC('/seed', [99])

# Pause / resume
op('oscout1').sendOSC('/pause', [1])   # pause
op('oscout1').sendOSC('/pause', [0])   # resume

# Cycle through consciousness_projection presets (0–6)
op('oscout1').sendOSC('/prompt_index', [2])
```

---

### 3b. NDI bridge (best quality, needs NDI SDK)

Install once:
```powershell
pip install ndi-python
# Also install NDI SDK from https://ndi.video/download-ndi-sdk/
```

Run:
```powershell
python touchdesigner/td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

In TouchDesigner:
- **NDI In TOP** → Source Name: `StreamDiffusion`
- **OSC Out CHOP** → `127.0.0.1:9000`
- **OSC In CHOP** → port `9001`

---

### 3c. Build your own .tox component

1. Start the NDI bridge (step 3b)
2. In TouchDesigner: `Tab` → **Text DAT** → paste contents of `touchdesigner/build_component.py`
3. Right-click the Text DAT → **Run Script**
4. `StreamDiffusionTD` Container COMP appears
5. Right-click → **Save Component As** → `StreamDiffusionTD.tox`

---

## 4. Configs reference

| Config | Model | Steps | FPS (RTX 2060) | VRAM | Notes |
|---|---|---|---|---|---|
| `configs/sdturbo_fast.yaml` | SD-Turbo (local) | 2 | **4.74** | 2.5 GB | Default — always works |
| `configs/sdturbo_tensorrt.yaml` | SD-Turbo + TRT | 2 | **5.83** | 4.5 GB | ~53s compile on first run, cached after |
| `configs/kohaku_quality.yaml` | Kohaku v2.1 + LCM-LoRA | 3 | **~3.4** | 2.7 GB | Better artistic quality |
| `configs/consciousness_projection.yaml` | SD-Turbo (local) | 2 | **~4.5** | 2.5 GB | Art/installation, 7 built-in prompts |

---

## 5. Benchmarks

```powershell
# xformers benchmark — measures real FPS, saves report to reports/
python scripts/research_benchmark.py --quick

# Full benchmark — adds Kohaku + 768p configs (~10 min)
python scripts/research_benchmark.py

# TensorRT benchmark — compiles engines (~53s first run), then benchmarks
python scripts/run_tensorrt_benchmark.py
```

Reports saved to `reports/benchmark_<timestamp>.md`.

**Measured on RTX 2060 6 GB, SD-Turbo, 512x512:**

| Acceleration | Steps | FPS | Latency | VRAM |
|---|---|---|---|---|
| xformers | 2 | **4.74** | 211 ms | 2,495 MB |
| xformers | 3 | **3.61** | 277 ms | 2,496 MB |
| TensorRT | 2 | **5.83** | 172 ms | ~4,500 MB |

See [`docs/benchmarks.md`](benchmarks.md) for full comparison including Kohaku and resolution scaling.

---

## 6. Acceleration modes

| Mode | When to use | VRAM | Notes |
|---|---|---|---|
| `xformers` | Default — use always | ~2.5 GB | Memory-efficient attention, works immediately |
| `tensorrt` | Maximum speed | ~4.5 GB | 53s compile on first run, ~3s load from cache |
| `none` | Debugging only | ~2.5 GB | Slow |

TensorRT engines cache in `engines/` and reload in ~3s on subsequent runs.

---

## 7. Parameter reference

| Parameter | Effect | Good range |
|---|---|---|
| `t_index_list` | Denoising step positions (0–50). More steps = better quality, lower FPS | `[35,45]` for 2-step, `[22,32,45]` for 3-step |
| `guidance_scale` | How strongly the prompt drives the output | 1.0–1.2 (above 1.5 too strong) |
| `cfg_type` | CFG strategy | `none` for SD-Turbo, `self` for SD 1.5/Kohaku |
| `strength` / `delta` | How much the input image is transformed | 0.5 = subtle, 0.9 = radical |
| `seed` | Starting noise value | Fix while tuning other params |
| `use_tiny_vae` | TAESD decoder (fast) vs full VAE (slow) | Always `True` for real-time |
| `use_denoising_batch` | Keeps N frames in a queue for throughput | Always `True` |
| `similar_image_filter` | Skip near-identical frames to reduce stuttering | Enable for noisy webcam |
