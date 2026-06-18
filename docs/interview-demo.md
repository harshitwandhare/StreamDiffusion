# StreamDiffusion — Interview Demo Guide

Position: Generative AI Systems Research Assistant II ($20/hr)
School of Arts, Humanities, and Technology — UTD

All commands verified end-to-end on RTX 2060 / Windows 10 / xformers 0.0.22.post7.

---

## Pre-flight check

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
python scripts/test_cuda.py
```

Expected output — confirm all lines before starting:
```
GPU: NVIDIA GeForce RTX 2060
xformers: 0.0.22.post7
All good. Ready to run StreamDiffusion.
```

---

## Demo sequence (run in this order)

### Demo 1 — Web UI — most visual, show first (~2 min)

```powershell
cd D:\Github\StreamDiffusion\demo\realtime-img2img
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080 --acceleration xformers
```

Open **http://localhost:8080** in browser.

- Webcam live on left, diffused output on right, updating continuously
- Type: `oil painting, impressionist, warm sunset` — watch style shift live
- Type: `neon cyberpunk, digital glitch, sharp edges` — immediate style change
- Say: "4.14 fps on RTX 2060, 2.5 GB VRAM"

Stop with `Ctrl+C`. Return to repo root:
```powershell
cd D:\Github\StreamDiffusion
```

> **Tip**: Must be run from `demo\realtime-img2img\` — server looks for `./frontend/public` relative to its own location.

---

### Demo 2 — TouchDesigner live generation (~5 min)

#### Step 1 — Start the Python backend

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

A preview window shows webcam input (left) and diffused output (right) with FPS overlay. Leave this terminal running.

#### Step 2 — Build the TD network (4 nodes, ~2 minutes)

Create these 4 nodes manually in TD. Full guide: [`docs/touchdesigner-setup.md`](touchdesigner-setup.md)

**Node 1 — Output image:** `Tab` → TOP tab → **File In**
- File: `D:/Github/StreamDiffusion/td_out/output_frame.png` (forward slashes)
- Cook Rate: `Every Frame`, Always Active: `On`
- Right-click → **View** → live diffused output appears

**Node 2 — OSC Out:** `Tab` → CHOP tab → **OSC Out**
- Network Address: `127.0.0.1`, Port: `9000`
- TD names this `oscout1` by default

**Node 3 — OSC In:** `Tab` → CHOP tab → **OSC In**
- Port: `9001`, Active: `On`
- `/fps`, `/vram_used`, `/status` channels appear from Python

**Node 4 — Control DAT:** `Tab` → DAT tab → **Text** → paste:
```python
osc = op('oscout1')
osc.sendOSC('/prompt',   ["vivid oil painting, golden hour, cinematic"])
osc.sendOSC('/strength', [0.6])
osc.sendOSC('/seed',     [42])
```
Edit prompt/strength → right-click → **Run Script** → Python updates live.

#### Step 3 — Change prompt and strength

Edit the values in the control DAT → right-click → **Run Script**:
- `strength = 0.3` → subtle (input clearly visible)
- `strength = 0.6` → balanced (default)
- `strength = 0.85` → heavy transform (very dreamlike)

#### Step 4 — Switch models from TD (hot-swap, ~20s reload)

Create one Text DAT per model → right-click → **Run Script**:

| Script | Model | FPS | VRAM |
|---|---|---|---|
| `op('oscout1').sendOSC('/model', ['configs/sdturbo_fast.yaml'])` | SD-Turbo | 4.14 | 2.5 GB |
| `op('oscout1').sendOSC('/model', ['configs/kohaku_quality.yaml'])` | Kohaku | ~3.4 | 2.7 GB |
| `op('oscout1').sendOSC('/model', ['configs/consciousness_projection.yaml'])` | Art | ~4.1 | 2.5 GB |
| `op('oscout1').sendOSC('/model', ['configs/sdturbo_tensorrt.yaml'])` | TensorRT | 5.59 | 4.5 GB |

Terminal shows `[OSC] model switch requested` → output freezes → resumes with new model.

#### Step 5 — Art installation presets

After switching to the art config, cycle 7 built-in prompts:
```python
op('oscout1').sendOSC('/prompt_index', [0])  # vivid digital painting
op('oscout1').sendOSC('/prompt_index', [3])  # bioluminescent deep sea
op('oscout1').sendOSC('/prompt_index', [5])  # neural lattice visualization
```

#### Step 6 — View live stats from OSC In CHOP

After running, the OSC In CHOP (port 9001) shows live channels from Python:
```
/fps          4.1
/vram_used    2495
/status       running
/model_name   sdturbo_fast
```

---

### Demo 3 — Benchmark — show real measured numbers (~1 min)

```powershell
python scripts/research_benchmark.py --quick
```

Output (actual measured, RTX 2060):
```
SD-Turbo 2-step  ->  4.14 fps  (241 ms/frame, 2495 MB VRAM)
SD-Turbo 3-step  ->  3.15 fps  (318 ms/frame, 2495 MB VRAM)
Report saved to: reports/benchmark_YYYYMMDD_HHMM.md
```

TensorRT benchmark (uses cached engines, ~3s load):
```powershell
python scripts/run_tensorrt_benchmark.py
```
Result: **5.59 fps**, 172 ms/frame.

---

### Demo 4 — Single image generation (~30 sec)

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

Text-to-image (Kohaku only — SD-Turbo is img2img only by design):
```powershell
python examples/txt2img/single.py `
  --prompt "a mountain at sunset, digital art, cinematic" `
  --acceleration xformers `
  --seed 42
```

---

## Interview question answers

### Q1 — Generative AI workflow (connects to: "develop and document generative AI workflows")

> "I installed and configured StreamDiffusion — the 2023 research pipeline — on an RTX 2060 running Windows. The core innovation is an assembly-line denoising batch queue: instead of finishing one image before starting the next, N frames stay in the pipeline simultaneously, so every GPU step produces output and throughput scales. I benchmarked multiple configurations: 2-step xformers gives 4.14 fps at 2.5 GB VRAM; TensorRT compiled engines give 5.59 fps but need 4.5 GB and a one-time 53-second compile that caches to disk. I use TAESD — Tiny AutoEncoder SD — for decoding; the full VAE alone takes 200ms per frame and destroys real-time throughput. I documented every config in YAML with comments, benchmarked each combination, and wrote step-by-step setup guides that a new collaborator can follow without my help. What I'd improve: the similar-image filter that skips near-duplicate frames helps for a static scene but increases perceived latency during fast movement — I'd make the threshold adaptive based on optical flow."

### Q2 — Technical troubleshooting (connects to: "troubleshoot software environments, dependencies, GPU workflows")

> "Three Windows-specific issues. First: TensorRT 9 crashed on import with `OSError: cannot load library cublas64_11.dll`. Root cause: Python's `ctypes.CDLL` on Windows searches the PATH after the venv directory, so CUDA Toolkit DLLs were invisible to TensorRT. Fix: wrote `tensorrt_loader.py` that calls `os.add_dll_directory()` for the CUDA bin path and pre-loads all 11 required DLLs explicitly before any TensorRT import. Second: YAML config files written by PowerShell had invisible UTF-8 BOM headers — `yaml.safe_load()` silently read the BOM as part of the first key name, so `model.id` came back as None. Fix: switch `open()` to `encoding='utf-8-sig'` which strips the BOM automatically. Third: Windows terminal cp1252 encoding crashed on the `→` Unicode arrow in print statements — fixed by replacing with ASCII `->` throughout. All three fixes are documented with the exact error messages so a future student hits the solution immediately."

### Q3 — Systems integration / TouchDesigner (connects to: "integrate AI workflows with TouchDesigner, OSC, creative platforms")

> "I connected StreamDiffusion to TouchDesigner using a PNG bridge: Python writes each processed frame to `td_out/output_frame.png`, TouchDesigner polls it with a File In TOP set to cook every frame — zero extra installs, works on any TD version. I also save the raw input frame to `input_frame.png` so TD can show input and output side-by-side. The setup in TD is 4 nodes: File In TOP for the output image, OSC Out CHOP sending to port 9000, OSC In CHOP receiving on port 9001, and a Text DAT with a control script the artist edits and runs to change prompt, strength, or seed. Bidirectional OSC: TD sends `/prompt`, `/strength`, `/seed`, `/model`, `/pause`; Python sends `/fps`, `/vram_used`, `/status`, `/model_name` back. I added hot-swap model switching — TD sends `/model configs/kohaku_quality.yaml`, Python releases GPU memory and reinitializes with the new model without restarting the script, ~20 second reload. For a live installation I'd add: a watchdog subprocess that auto-restarts Python on crash, error logging with last-prompt and VRAM state, and a thermal soak test before public opening."

### Q4 — Documentation (connects to: "document technical processes clearly for interdisciplinary collaborators")

> "I structured the docs so each file answers a specific question for a specific reader. `docs/all-run-modes.md` is the operational reference — every way to run the system with exact PowerShell commands, a verified-status table (WORKS / BROKEN with reason), and a parameter reference table. `docs/touchdesigner-setup.md` covers the TD integration in two paths: an auto-build script that constructs the node network programmatically, and a manual step-by-step for understanding each node individually — because a collaborating artist needs the visual walkthrough, not just the script. `docs/benchmarks.md` has measured numbers with hardware specs so any collaborator can assess whether their GPU is comparable before investing setup time. `docs/windows-tensorrt.md` documents the DLL fix with the exact error message so someone hitting the same crash searches the error and finds the solution immediately. I explicitly mark broken upstream features with the error and reason — `demo/realtime-txt2img` fails with a TypeScript type error in @mantine/core, `txt2img/single.py` only works with Kohaku because SD-Turbo is img2img-only by design. Honest status matters in a research environment."

### Q5 — HPC / JUNO (if asked — connects to: "configure and run AI jobs on UTD JUNO HPC")

> "I haven't used JUNO specifically, but I've worked with GPU batch job workflows on Windows. The core concepts transfer: resource allocation for long inference or training jobs, managing checkpoints so a preempted job can resume, and writing reproducible environment setup scripts. On JUNO with Slurm I'd use `sbatch` for long training or large-batch inference jobs with a defined VRAM requirement and walltime, and `srun` for interactive debugging sessions. The main new surface for me would be module loading for CUDA and conda environment setup in the job script — I'd want to verify the exact CUDA version on JUNO matches the PyTorch build before submitting anything GPU-dependent. I'm comfortable getting up to speed on this independently."

### Tier II justification (say this if asked directly)

> "Evidence: I diagnosed two Windows-specific crashes not documented anywhere — the TensorRT DLL load order issue and the YAML UTF-8 BOM corruption — and wrote targeted fixes for both. I benchmarked the pipeline across four acceleration modes with actual measured numbers. I built the TouchDesigner integration layer from scratch: the PNG bridge, OSC bidirectional control, hot-swap model switching, and a programmatic network-builder that creates the full TD interface automatically. I documented everything at the level where a student with no prior StreamDiffusion exposure can reproduce the full setup. That's the practical bar for Tier II — build it, break it, fix it, document it well enough that you're not the bottleneck."

---

## Quick reference — all verified commands

### Environment

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
python scripts/test_cuda.py
```

### Web demo

```powershell
cd D:\Github\StreamDiffusion\demo\realtime-img2img
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080 --acceleration xformers
# Open http://localhost:8080
```

### TouchDesigner bridge

```powershell
cd D:\Github\StreamDiffusion
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

### Benchmarks

```powershell
python scripts/research_benchmark.py --quick          # xformers: ~4.1 fps
python scripts/run_tensorrt_benchmark.py              # TRT: ~5.6 fps (cached)
```

### Single image

```powershell
python examples/img2img/single.py `
  --model_id_or_path "D:\Github\StreamDiffusion\models\sd-turbo" `
  --prompt "vivid oil painting, golden hour, cinematic" `
  --acceleration xformers --cfg_type none --guidance_scale 1.0 --seed 42

python examples/txt2img/single.py `
  --prompt "a mountain at sunset, digital art, cinematic" `
  --acceleration xformers --seed 42
```

### Screen capture (requires display)

```powershell
python examples/screen/main.py `
  --model_id_or_path "D:\Github\StreamDiffusion\models\sd-turbo" `
  --prompt "oil painting, impressionist style" `
  --acceleration xformers `
  --cfg_type self
```

### OSC control from TD (in any Text DAT → right-click → Run Script)

```python
# oscout1 is the default name TD gives to the first OSC Out CHOP you place
op('oscout1').sendOSC('/prompt',       ['abstract generative art, flowing light'])
op('oscout1').sendOSC('/strength',     [0.75])
op('oscout1').sendOSC('/seed',         [42])
op('oscout1').sendOSC('/pause',        [1])    # 1=pause, 0=resume
op('oscout1').sendOSC('/model',        ['configs/kohaku_quality.yaml'])
op('oscout1').sendOSC('/prompt_index', [3])    # art preset 3
```

---

## Configs

| File | Model | FPS | VRAM | Notes |
|---|---|---|---|---|
| `configs/sdturbo_fast.yaml` | SD-Turbo (local) | **4.14** | 2.5 GB | Default — always works |
| `configs/sdturbo_tensorrt.yaml` | SD-Turbo + TRT | **5.59** | 4.5 GB | ~53s compile first run, cached after |
| `configs/kohaku_quality.yaml` | Kohaku v2.1 + LCM-LoRA | **~3.4** | 2.7 GB | Better artistic quality |
| `configs/consciousness_projection.yaml` | SD-Turbo (local) | **~4.5** | 2.5 GB | 7 art presets |

---

## Known broken (upstream — cannot be fixed)

| Item | Error | Why it's broken |
|---|---|---|
| `demo/realtime-txt2img` frontend | TypeScript TS1005 in @mantine/core types | Upstream package version mismatch |
| `examples/txt2img/single.py` with SD-Turbo | Tensor batch size mismatch in scheduler | SD-Turbo is img2img only by architecture |
