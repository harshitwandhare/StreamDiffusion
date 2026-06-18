# Interview Demo Guide — StreamDiffusion

## Pre-flight checklist

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
python scripts/test_cuda.py
```

Expected output — confirm all three lines before starting:
```
GPU: NVIDIA GeForce RTX 2060
xformers: 0.0.22.post7
All good. Ready to run StreamDiffusion.
```

---

## Demo sequence (in this order)

### 1. Web UI demo — most visual, show first (~2 min)

```powershell
cd D:\Github\StreamDiffusion\demo\realtime-img2img
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080 --acceleration xformers
```

Open **http://localhost:8080** in browser.

What to show:
- Webcam on left, diffused output on right updating live
- Type a prompt: `"oil painting, impressionist, warm sunset"` → watch output shift
- Type: `"neon cyberpunk, digital glitch, sharp edges"` → style changes live
- Mention: "4.8 fps on RTX 2060, 2.5 GB VRAM"

To switch to Kohaku model (better artistic quality, slower):
```powershell
# Ctrl+C first, then:
python main.py --port 8080 --model_id_or_path KBlueLeaf/kohaku-v2.1 --acceleration xformers
```

Press `Ctrl+C` when done, go back to repo root.

---

### 2. TouchDesigner live generation (~5 min)

**Terminal — start the Python backend:**
```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```
Wait for: `[INIT] Model ready.` and `[RUN] Streaming.`

**TouchDesigner — build the network:**

Step 1 — Display output:
- `Tab` → **File In TOP**
- File: `D:/Github/StreamDiffusion/td_out/current_frame.png`
- Cook: `Every Frame`, Always Active: `On`
- Live diffused frames appear

Step 2 — OSC control:
- `Tab` → **OSC Out CHOP** → Address: `127.0.0.1`, Port: `9000`
- `Tab` → **OSC In CHOP** → Port: `9001`
- OSC In CHOP shows `/fps`, `/vram_used`, `/status` live

Step 3 — Live prompt from TouchDesigner:
- `Tab` → **Text DAT** → right-click → **Run Script**:
  ```python
  op('oscout1').sendOSC('/prompt', ['abstract generative art, flowing light, ethereal'])
  ```
- Prompt updates mid-stream without restarting

**Switch models in TD demo:**
- In terminal: `Ctrl+C`
- Run: `python touchdesigner/td_bridge.py --config configs/kohaku_quality.yaml --webcam 0`
- Wait for model ready → TD File In TOP picks up automatically

**Switch to art installation mode (7 preset prompts):**
```powershell
python touchdesigner/td_bridge.py --config configs/consciousness_projection.yaml --webcam 0
```
Cycle presets via OSC:
```python
op('oscout1').sendOSC('/prompt_index', [0])  # first preset
op('oscout1').sendOSC('/prompt_index', [3])  # fourth preset
```

---

### 3. Benchmark — show measured numbers (~1 min)

```powershell
python scripts/research_benchmark.py --quick
```

Output:
```
SD-Turbo 2-step  ->  4.8 fps  (210 ms/frame, 2495 MB VRAM)
SD-Turbo 3-step  ->  3.6 fps  (275 ms/frame, 2497 MB VRAM)
Report saved to: reports/benchmark_YYYYMMDD_HHMM.md
```

For TensorRT (~23% faster, first run ~53s compile):
```powershell
python scripts/run_tensorrt_benchmark.py
```
Result: ~5.8 fps, 172 ms/frame.

---

### 4. Single image generation (show the pipeline concept)

```powershell
python examples/img2img/single.py `
  --model_id_or_path "D:\Github\StreamDiffusion\models\sd-turbo" `
  --prompt "vivid oil painting, golden hour, cinematic" `
  --acceleration xformers `
  --cfg_type none `
  --guidance_scale 1.0 `
  --seed 42
```

Output saved to `images/outputs/output.png`.

---

## Interview question answers

### Q1 — Generative AI workflow

> "I installed and configured StreamDiffusion — the research pipeline from the 2023 paper — locally on an RTX 2060. The core idea is an assembly-line denoising batch: instead of completing one image before starting the next, it keeps N frames in a queue so every GPU cycle produces output, enabling real-time generation. I benchmarked multiple configurations: 2-step xformers gives 4.8 fps at 2.5 GB VRAM; TensorRT adds 23% speed but needs 4.5 GB and a one-time 53-second engine compile. I use TAESD (Tiny AutoEncoder) for decoding — the full VAE decoder alone takes ~200ms per frame, which destroys real-time throughput. What I'd improve: the similar-image filter that skips near-duplicate frames helps for noisy webcam but increases perceived latency for fast-moving scenes — I'd make it adaptive."

### Q2 — Technical troubleshooting

> "TensorRT 9 on Windows wouldn't load at all — Python crashed with `OSError: cannot load library cublas64_11.dll`. The fix wasn't obvious. I traced it to Windows DLL load order: TensorRT calls `ctypes.CDLL` on 11 specific DLLs in sequence, but Windows searches the PATH only after the venv's directory, so `cublas64_11.dll` from CUDA Toolkit was invisible. I wrote `tensorrt_loader.py` that pre-loads all 11 DLLs explicitly using `os.add_dll_directory()` and `ctypes.CDLL()` before any TensorRT import. Second issue: YAML config files written by PowerShell had UTF-8 BOM headers that `yaml.safe_load()` silently corrupted, causing `KeyError: 'model'`. Fixed by switching `open()` to `encoding='utf-8-sig'` which strips the BOM automatically. Third: Windows terminal crashed on the `→` Unicode arrow character in print statements — Windows console defaults to cp1252 which can't encode it. Fixed by replacing with ASCII `->` everywhere."

### Q3 — Systems integration

> "I connected StreamDiffusion to TouchDesigner using two methods. The PNG bridge writes each processed frame to `td_out/current_frame.png` — TouchDesigner polls it with File In TOP, works with zero extra installs. The NDI bridge streams output as a proper video source — TouchDesigner picks it up as an NDI In TOP with near-zero latency. Both use OSC for bidirectional control: TouchDesigner sends `/prompt`, `/strength`, `/seed`, `/pause` to port 9000; the Python backend sends `/fps`, `/vram_used`, `/status` back on port 9001. Key design decision: live inference vs pre-rendered. Live is needed when a performer is controlling the prompt in real time. Pre-rendered loops are better for long unattended installations because they eliminate the risk of GPU OOM or model crash during a show. For a public installation I'd add a watchdog process that restarts the Python backend if it exits, log every crash with timestamp and last prompt, and do a 4-hour thermal soak test before opening."

### Q4 — Documentation

> "I structured the docs so each file answers a specific question: `docs/all-run-modes.md` is the operational reference — every way to run the system with exact commands; `docs/touchdesigner-setup.md` is the TD integration guide with step-by-step screenshots-equivalent instructions; `docs/benchmarks.md` has the measured performance numbers with hardware specs so anyone can assess whether their GPU is comparable; `docs/windows-tensorrt.md` documents the DLL fix with the exact error message so someone hitting the same crash can find the solution immediately. The configs use nested YAML (`model.id`, `inference.acceleration`) with commented fields so a new contributor can understand the settings without reading the source code. Everything is version-controlled on a separate branch from the upstream repo so the diff is exactly the Windows-specific additions."

### Tier II justification

> "Tier II. I didn't just follow instructions — I diagnosed two Windows-specific crashes that weren't documented anywhere, wrote the fixes, benchmarked the pipeline across multiple acceleration methods, and built the TouchDesigner integration layer from scratch. Evidence: `tensorrt_loader.py` with the 11 DLL pre-load sequence; benchmark reports showing 4.74 fps xformers and 5.83 fps TensorRT on this specific hardware; `touchdesigner/td_bridge.py` with the OSC bidirectional control protocol. The system is fully documented so someone else can reproduce it without my help."

---

## Quick reference — all configs

| Config file | Model | FPS | VRAM | Use case |
|---|---|---|---|---|
| `sdturbo_fast.yaml` | SD-Turbo local | **4.8** | 2.5 GB | Default for everything |
| `sdturbo_tensorrt.yaml` | SD-Turbo + TRT | **5.8** | 4.5 GB | Max speed (53s first compile) |
| `kohaku_quality.yaml` | Kohaku v2.1 + LCM-LoRA | **3.4** | 2.7 GB | Better artistic quality |
| `consciousness_projection.yaml` | SD-Turbo local | **4.5** | 2.5 GB | Art/installation, 7 presets |

## Quick reference — all runnable scripts

| Script | What it does | Command |
|---|---|---|
| `scripts/test_cuda.py` | Verify GPU/CUDA/xformers | `python scripts/test_cuda.py` |
| `scripts/research_benchmark.py` | Benchmark xformers, save report | `python scripts/research_benchmark.py --quick` |
| `scripts/run_tensorrt_benchmark.py` | Benchmark TensorRT | `python scripts/run_tensorrt_benchmark.py` |
| `touchdesigner/td_bridge.py` | TD PNG bridge (webcam → file → TD) | `python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0` |
| `touchdesigner/td_ndi_bridge.py` | TD NDI bridge (needs NDI SDK) | `python touchdesigner/td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam 0` |
| `demo/realtime-img2img/main.py` | Web UI, webcam → browser | `cd demo/realtime-img2img && python main.py --port 8080` |
| `examples/img2img/single.py` | Single image in → image out | `python examples/img2img/single.py --model_id_or_path ...` |
