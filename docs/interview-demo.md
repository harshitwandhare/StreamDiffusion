# StreamDiffusion — Interview Demo Guide

All commands verified on RTX 2060 / Windows 10 / xformers 0.0.22.post7.

---

## Pre-flight (run before interview)

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
python scripts/test_cuda.py
```

Expected:
```
GPU: NVIDIA GeForce RTX 2060
xformers: 0.0.22.post7
All good. Ready to run StreamDiffusion.
```

If this fails: restart terminal, re-activate `.venv\Scripts\activate`, run again.

---

## Demo sequence

### 1. Web UI — most visual, show first (~2 min)

```powershell
cd D:\Github\StreamDiffusion\demo\realtime-img2img
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080 --acceleration xformers
```

Open **http://localhost:8080** in browser.

What to show:
- Webcam live on left, diffused output on right, updating continuously
- Type prompt: `oil painting, impressionist, warm sunset` — watch style shift live
- Type prompt: `neon cyberpunk, digital glitch, sharp edges` — instant style change
- Say: "4.74 fps on RTX 2060, 2.5 GB VRAM. The assembly-line denoising batch is why it's real-time — instead of finishing one image before starting the next, N frames are in the queue simultaneously."

Stop with Ctrl+C. Return to repo root:
```powershell
cd D:\Github\StreamDiffusion
```

---

### 2. TouchDesigner live generation (~5 min)

Full guide: `docs/touchdesigner-setup.md`

**Step 1 — start the Python backend:**

```powershell
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

Wait for:
```
[INIT] Model ready.
[RUN] Streaming.
      Model:  sdturbo_fast
      Output: td_out/
      Frames: input_frame.png  |  output_frame.png  |  current_frame.png
      OSC in: port 9000   out: port 9001
```

A preview window appears: **webcam input on the left, diffused output on the right** with FPS overlay.

**Step 2 — in TouchDesigner, build the network:**

Option A — auto-build (30 seconds):
1. Tab → **Text DAT** → place it
2. Paste entire `touchdesigner/td_network_builder.py` into the DAT
3. Right-click → **Run Script**
4. `/StreamDiffusion` container is created with all nodes

Option B — manual (show you understand every node):
1. Tab → **File In TOP** → `input_view`
   - File: `D:/Github/StreamDiffusion/td_out/input_frame.png`
   - Cook Rate: `Every Frame`, Always Active: `On`
2. Tab → **File In TOP** → `output_view`
   - File: `D:/Github/StreamDiffusion/td_out/output_frame.png`
   - Cook Rate: `Every Frame`, Always Active: `On`
3. Tab → **OSC Out CHOP** → `osc_out` → Address: `127.0.0.1`, Port: `9000`
4. Tab → **OSC In CHOP** → `osc_in` → Port: `9001` → shows /fps /vram_used /status live
5. Tab → **Text DAT** → `prompt_text` → type your prompt
6. Tab → **DAT Execute DAT** → `executor` → paste the controller script (see touchdesigner-setup.md)

**Step 3 — change prompt live from TouchDesigner:**

Double-click `prompt_text` DAT → edit the text. The executor DAT auto-sends OSC to Python on every change.

Or send manually:
```python
# In a Text DAT -> right-click -> Run Script:
op('osc_out').sendOSC('/prompt', ['abstract generative art, flowing light, ethereal'])
```

**Step 4 — adjust strength (noise level):**

```python
op('osc_out').sendOSC('/strength', [0.75])   # 0.0 = no change, 1.0 = full transform
```

Or edit `strength_text` DAT to `0.75` — executor sends it automatically.

**Step 5 — switch models from TD (hot-swap, ~20s reload):**

Right-click the model DAT → Run Script:
```python
# switch_kohaku
op('osc_out').sendOSC('/model', ['configs/kohaku_quality.yaml'])
```

| What to say | Numbers |
|---|---|
| SD-Turbo fast | 4.74 fps, 2.5 GB VRAM |
| Kohaku quality | ~3.4 fps, 2.7 GB VRAM |
| TensorRT | 5.83 fps, 4.5 GB VRAM |

**Step 6 — art installation mode (consciousness_projection config):**

```powershell
# Stop current bridge (Ctrl+C), then:
python touchdesigner/td_bridge.py --config configs/consciousness_projection.yaml --webcam 0
```

Or hot-swap from TD:
```python
op('osc_out').sendOSC('/model', ['configs/consciousness_projection.yaml'])
```

Cycle through 7 art presets:
```python
op('osc_out').sendOSC('/prompt_index', [0])   # preset 0
op('osc_out').sendOSC('/prompt_index', [3])   # preset 3 — sacred geometry
op('osc_out').sendOSC('/prompt_index', [5])   # preset 5 — neural lattice
```

---

### 3. Benchmark — show measured numbers (~1 min)

```powershell
python scripts/research_benchmark.py --quick
```

Output:
```
SD-Turbo 2-step  ->  4.7 fps  (211 ms/frame, 2495 MB VRAM)
SD-Turbo 3-step  ->  3.6 fps  (277 ms/frame, 2496 MB VRAM)
Report saved to: reports/benchmark_YYYYMMDD_HHMM.md
```

Say: "4.74 fps vs 100+ fps on RTX 4090 from the paper — expected, RTX 2060 has 3-5x fewer tensor cores and 3x lower memory bandwidth. TensorRT adds 23% on top."

For TensorRT benchmark (~53s compile on first run, cached after):
```powershell
python scripts/run_tensorrt_benchmark.py
```
Result: 5.83 fps, 172 ms/frame.

---

### 4. Single image generation (~30s)

Shows the raw pipeline with no webcam dependency:

```powershell
python examples/img2img/single.py `
  --model_id_or_path "D:\Github\StreamDiffusion\models\sd-turbo" `
  --prompt "vivid oil painting, golden hour, cinematic" `
  --acceleration xformers `
  --cfg_type none `
  --guidance_scale 1.0 `
  --seed 42
```

Output: `images/outputs/output.png` (~190 KB, 512x512).

Text-to-image (Kohaku model only — SD-Turbo is img2img only):
```powershell
python examples/txt2img/single.py `
  --prompt "a mountain at sunset, digital art, cinematic" `
  --acceleration xformers `
  --seed 42
```

---

## Interview question answers

### Q1 — Generative AI workflow

> "I installed and configured StreamDiffusion — the 2023 research pipeline — on an RTX 2060. The core innovation is assembly-line denoising: instead of completing one image before starting the next, N frames stay in a denoising queue simultaneously, so every GPU step produces useful output and throughput scales with batch size. I benchmarked multiple configurations: 2-step xformers gives 4.74 fps at 2.5 GB VRAM, TensorRT adds 23% to 5.83 fps but needs 4.5 GB and a one-time 53-second engine compile. I use TAESD — Tiny AutoEncoder SD — for decoding; the full VAE alone costs 200ms per frame and destroys real-time throughput. What I'd improve: the similar-image filter skips near-duplicate frames which reduces GPU load on a static scene, but increases perceived latency during fast movement — I'd make the threshold adaptive based on optical flow magnitude."

### Q2 — Technical troubleshooting

> "Three Windows-specific issues. First: TensorRT 9 crashed on import with `OSError: cannot load library cublas64_11.dll`. Traced it to Windows DLL search order — Python's ctypes.CDLL searches the PATH after the venv directory, so CUDA Toolkit DLLs were invisible. Fix: wrote `tensorrt_loader.py` that calls `os.add_dll_directory()` and pre-loads all 11 required DLLs before any TensorRT import. Second: YAML config files written by PowerShell had UTF-8 BOM headers that `yaml.safe_load()` silently corrupted — `model.id` came back as None. Fix: switch `open()` to `encoding='utf-8-sig'` which strips the BOM. Third: Windows terminal cp1252 encoding crashed on the `→` Unicode arrow in print statements. Fix: replace all `→` with ASCII `->`."

### Q3 — Systems integration

> "Connected StreamDiffusion to TouchDesigner using a PNG bridge: Python writes each processed frame to `td_out/output_frame.png`, TouchDesigner polls it with File In TOP set to cook every frame — zero extra installs, works immediately. I also save the raw input frame to `input_frame.png` so TD can show input and output side-by-side. Bidirectional OSC control: TD sends `/prompt`, `/strength`, `/seed`, `/model`, `/pause` to port 9000; Python sends `/fps`, `/vram_used`, `/status`, `/model_name` back on port 9001. I added hot-swap model switching — TD sends `/model configs/kohaku_quality.yaml` via OSC, Python reinitializes the StreamDiffusion pipeline on the fly while freezing the last output frame. For a public installation I'd add a watchdog process that restarts the Python backend on crash, log every failure with the last prompt and VRAM state, and do a 4-hour thermal soak before opening."

### Q4 — Documentation

> "Structured the docs so each file answers a specific question: `docs/all-run-modes.md` is the operational reference — every way to run the system with exact PowerShell commands and a status table showing what's working vs. broken; `docs/touchdesigner-setup.md` is the TD integration guide with both an auto-build script that constructs the node network programmatically and a manual step-by-step for understanding each node; `docs/benchmarks.md` has the measured numbers with hardware specs so anyone can assess comparability; `docs/windows-tensorrt.md` documents the DLL fix with the exact error message so someone hitting the same crash finds the solution immediately. The configs use nested YAML with comments on every field so a new contributor understands the settings without reading source. I marked upstream-broken features explicitly: `demo/realtime-txt2img` has a TypeScript build error in @mantine/core, and `examples/txt2img/single.py` only works with Kohaku — SD-Turbo in txt2img mode hits a batch size mismatch in the scheduler."

### Tier II justification

> "Evidence: I diagnosed two Windows-specific crashes not documented anywhere — the TensorRT DLL load order issue and the YAML UTF-8 BOM corruption — and wrote specific fixes for both. I benchmarked the pipeline across four acceleration modes and two models with actual measured numbers, not estimates. I built the TouchDesigner integration layer: the PNG bridge, the OSC bidirectional control protocol, hot-swap model switching, and a programmatic network-builder script that constructs the full TD interface automatically. The system is documented well enough for someone else to reproduce it without my help, which is the practical test of Tier II work."

---

## Quick reference tables

### Configs

| File | Model | FPS | VRAM | Notes |
|---|---|---|---|---|
| `configs/sdturbo_fast.yaml` | SD-Turbo (local) | 4.74 | 2.5 GB | Default for everything |
| `configs/sdturbo_tensorrt.yaml` | SD-Turbo + TRT | 5.83 | 4.5 GB | ~53s compile first run |
| `configs/kohaku_quality.yaml` | Kohaku v2.1 + LCM-LoRA | ~3.4 | 2.7 GB | Better artistic quality |
| `configs/consciousness_projection.yaml` | SD-Turbo (local) | ~4.5 | 2.5 GB | 7 art presets |

### All runnable scripts

| Script | Purpose | Command |
|---|---|---|
| `scripts/test_cuda.py` | Verify GPU + xformers | `python scripts/test_cuda.py` |
| `scripts/research_benchmark.py` | Measure FPS, save report | `python scripts/research_benchmark.py --quick` |
| `scripts/run_tensorrt_benchmark.py` | TRT FPS measurement | `python scripts/run_tensorrt_benchmark.py` |
| `touchdesigner/td_bridge.py` | TD PNG bridge — main TD integration | `python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0` |
| `touchdesigner/td_ndi_bridge.py` | TD NDI bridge (needs NDI SDK) | `python touchdesigner/td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam 0` |
| `touchdesigner/td_network_builder.py` | Auto-builds TD interface | Run inside TD as Text DAT |
| `demo/realtime-img2img/main.py` | Web UI webcam → browser | `cd demo\realtime-img2img && python main.py --port 8080` |
| `examples/img2img/single.py` | Single image in → image out | `python examples/img2img/single.py --model_id_or_path models/sd-turbo ...` |
| `examples/txt2img/single.py` | Text → image (Kohaku only) | `python examples/txt2img/single.py --prompt "..."` |
| `examples/screen/main.py` | Screen capture → live window | `python examples/screen/main.py --prompt "..."` |

### Known broken (upstream issues, not fixable)

| Item | Error | Notes |
|---|---|---|
| `demo/realtime-txt2img` frontend | TypeScript TS1005 in @mantine/core | Upstream version conflict |
| `examples/txt2img/single.py` with SD-Turbo | Tensor batch size mismatch | SD-Turbo is img2img only; use Kohaku |
