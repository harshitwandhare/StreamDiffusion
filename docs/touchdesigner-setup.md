# TouchDesigner + StreamDiffusion — Complete Setup Guide

This covers all three integration methods in order from simplest to best quality.
**For the interview demo, use Method C first (zero extra installs), then upgrade to Method B if NDI SDK is installed.**

---

## Architecture overview

```
Webcam / noise / image
        │
        ▼
  Python backend (td_bridge.py or td_ndi_bridge.py)
  - reads each webcam frame via OpenCV
  - runs StreamDiffusion img2img inference on GPU
  - applies your text prompt as a style guide
        │
        ├── PNG file → td_out/current_frame.png  (Method C)
        └── NDI video stream "StreamDiffusion"    (Method B)
        │
        ▼
  TouchDesigner receives the output as a TOP
  - File In TOP polls the PNG (Method C)
  - NDI In TOP receives the stream (Method B)
        │
        ▼
  OSC control (both methods):
  TouchDesigner → port 9000 → Python  (send /prompt /strength /seed /pause)
  Python        → port 9001 → TD      (receive /fps /vram_used /status)
```

---

## Method C — PNG bridge (recommended for demo, zero extra installs)

### Step 1: Start the Python backend

Open a terminal, activate venv:
```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
```

Start with SD-Turbo (fastest, ~4.8 fps):
```powershell
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

Wait for:
```
[INIT] Loading model: D:\Github\StreamDiffusion\models\sd-turbo
[INIT] Model ready.
[RUN] Streaming. Ctrl+C to stop.
```

To switch models, stop (Ctrl+C) and re-run with a different config:
```powershell
# Kohaku — better artistic quality, ~3.4 fps
python touchdesigner/td_bridge.py --config configs/kohaku_quality.yaml --webcam 0

# 7 art preset prompts (consciousness projection)
python touchdesigner/td_bridge.py --config configs/consciousness_projection.yaml --webcam 0

# TensorRT — fastest, ~5.8 fps, ~53s compile on first run only
python touchdesigner/td_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam 0
```

### Step 2: Set up TouchDesigner

Open TouchDesigner 2023. In the network editor:

**A. Add File In TOP** (displays the live output)
1. Press `Tab` → type `File In` → place it
2. In parameters (right panel):
   - **File** → `D:/Github/StreamDiffusion/td_out/current_frame.png`
   - **Cook** → `Every Frame`
   - **Always Active** → `On` (toggle the checkbox)
3. You should see the live diffused webcam frame updating in real time

**B. Add OSC Out CHOP** (send prompts/controls to Python)
1. `Tab` → type `OSC Out` → place it
2. Parameters:
   - **Network Address** → `127.0.0.1`
   - **Network Port** → `9000`

**C. Add OSC In CHOP** (receive FPS/VRAM stats from Python)
1. `Tab` → type `OSC In` → place it
2. Parameters:
   - **Network Address** → `127.0.0.1` (or `0.0.0.0`)
   - **Network Port** → `9001`
3. You'll see `/fps`, `/vram_used`, `/status` channels update live

### Step 3: Send OSC control from TouchDesigner

In a **Text DAT** (right-click → Run on any key event, or use a Script CHOP):
```python
# Change prompt live
op('oscout1').sendOSC('/prompt', ['dreamlike impressionist painting, swirling colors'])

# Adjust how much the prompt transforms the input (0.0 = no change, 1.0 = full transform)
op('oscout1').sendOSC('/strength', [0.75])

# Change seed (different random noise pattern)
op('oscout1').sendOSC('/seed', [123])

# Pause / resume
op('oscout1').sendOSC('/pause', [1])   # 1 = pause
op('oscout1').sendOSC('/pause', [0])   # 0 = resume

# Switch to a different preset prompt (consciousness_projection config only)
op('oscout1').sendOSC('/prompt_index', [2])   # 0-6
```

**To make a live typing prompt box:**
1. `Tab` → add a **Text COMP**
2. Set: Multi-line = On, Editable Continuous Update = On
3. Drag it onto the OSC Out CHOP's `/prompt` message → **Reference**
4. Every keystroke now updates the generation

---

## Method B — NDI bridge (best quality, requires NDI SDK)

### Prerequisites (one-time install)

1. **NDI SDK** — download from https://ndi.video/download-ndi-sdk/ → install
2. **ndi-python package**:
   ```powershell
   cd D:\Github\StreamDiffusion
   .venv\Scripts\activate
   pip install ndi-python
   ```

### Step 1: Start the NDI backend

```powershell
python touchdesigner/td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

Wait for:
```
[ready] StreamDiffusion active — NDI source: 'StreamDiffusion'
        In TouchDesigner: NDI In TOP -> select 'StreamDiffusion'
```

### Step 2: TouchDesigner network

**A. Add NDI In TOP**
1. `Tab` → type `NDI In` → place it
2. Parameters:
   - **Source Name** → `StreamDiffusion` (appears in the dropdown once the bridge is running)
   - **Band Width** → `Highest` (for lowest latency)
3. Live video appears immediately — no file polling, lower latency than Method C

**B. OSC setup** — same as Method C above (ports 9000 and 9001).

### Why NDI over PNG?
| | PNG bridge | NDI bridge |
|---|---|---|
| Extra install | None | NDI SDK + ndi-python |
| Latency | +50-100ms (file I/O) | Near-zero |
| Max throughput | Limited by disk write | Full GPU speed |
| Fallback | Always works | Needs SDK |

---

## Method A — dotsimulate .tox (commercial, $10 Patreon)

The video tutorial uses a pre-built `.tox` operator from dotsimulate's Patreon.
This repo replicates everything it does for free via Methods B/C above.

If you have the `.tox`:
1. Drag it into your TD network
2. Setup page → **Base Folder**: `D:\Github\StreamDiffusion`
3. Click **"Install NDI and Spout requirements only"** (SD is already installed)
4. Wait for install complete → **Start Stream**

**Do NOT click "Download and Update SD"** — it will re-clone the repo and overwrite your setup.

---

## Changing models mid-session

All models require a restart of the Python backend. There is no hot-swap.

| Config | Model | Steps | FPS | VRAM | Best for |
|---|---|---|---|---|---|
| `sdturbo_fast.yaml` | SD-Turbo (local) | 2 | **4.8** | 2.5 GB | Default, always works |
| `sdturbo_tensorrt.yaml` | SD-Turbo + TRT | 2 | **5.8** | 4.5 GB | Max speed (53s compile first run) |
| `kohaku_quality.yaml` | Kohaku v2.1 + LCM-LoRA | 3 | **3.4** | 2.7 GB | Better artistic quality |
| `consciousness_projection.yaml` | SD-Turbo (local) | 2 | **4.5** | 2.5 GB | Art install, 7 preset prompts |

To switch: `Ctrl+C` in the terminal → re-run with different config → File In TOP or NDI In TOP reconnects automatically.

---

## Common issues

| Problem | Cause | Fix |
|---|---|---|
| Black frame in File In TOP | Path wrong or backend not started | Check path uses forward slashes `D:/Github/...`; wait for `[INIT] Model ready` |
| NDI source not showing | NDI SDK not installed, or bridge not running | Install NDI SDK first, then pip install ndi-python |
| OSC not responding | Wrong port or CHOP not active | Confirm OSC Out port is 9000; click the CHOP and press `A` to activate |
| Low FPS in TD | File In TOP cooking too fast | Set Cook to `Every Frame` only (not `Pulse`) |
| `[ERROR] Cannot open webcam 0` | Webcam index wrong | Try `--webcam 1` or `--webcam 2` |
| Model loads then crashes | OOM on 6 GB GPU | Close all other GPU apps; use `sdturbo_fast.yaml` not TRT |
