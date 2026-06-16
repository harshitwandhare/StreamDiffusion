# TouchDesigner Integration

Two ways to connect StreamDiffusion to TouchDesigner 2023. Start with **Method A** — it gives you a full UI inside TD, model switching, LoRA support, and NDI/Spout streaming at full quality. Use **Method B** if you can't install NDI or want a zero-dependency quick test.

---

## Method A: StreamDiffusionTD Operator (recommended)

This is the approach shown in the dotsimulate tutorial. A pre-built `.tox` operator manages the Python backend from inside TouchDesigner. You get a proper UI for all parameters, NDI/Spout video (no polling PNG files), LoRA support, and live model switching.

### Prerequisites

Before opening TouchDesigner:

1. **NDI SDK** — download and install from https://ndi.video/download-ndi-sdk/
2. **Git** — must be in PATH. Download from https://git-scm.com/download/win (check "Add to PATH" during install)
3. **Python 3.10** — must be in PATH (not 3.11+)
4. **Your StreamDiffusion install** — already done at `D:\Github\StreamDiffusion`

### Setup (one time)

1. Download the **StreamDiffusionTD .tox** from dotsimulate's Patreon (link in the YouTube video description)
2. In TouchDesigner 2023: drag the `.tox` file into your network
3. On the **Setup page** of the operator:
   - Set **Base Folder** → `D:\Github\StreamDiffusion`
   - Set **Stream Type** → NDI (or Spout — both run at similar speed)
   - Click **"Install NDI and Spout requirements only"** (since SD is already installed — do NOT click "Download and Update SD" or it will re-clone the repo)
4. Wait for "installation finished" in the command window, then press any key

### Starting the stream

1. On the **Settings page**:
   - **Model ID/Path** → `stabilityai/sd-turbo` (downloads automatically) or local path e.g. `D:/Github/StreamDiffusion/models/sd-turbo`
   - **Step Schedule** → set to 2 steps for real-time speed, 4 for better quality
   - **Similar Image Filter** → leave off unless you have a noisy webcam
2. Click **"Start Stream"** — a command window opens and loads the model
3. Wait for `stream active` + FPS info in the command window

### Connecting your input

The operator takes any TOP as input (webcam, noise, video, image, etc.):

```
[Noise TOP or Webcam TOP] ──▶ [StreamDiffusionTD operator] ──▶ [your network]
```

**If the NDI output doesn't appear**: click the X on the left of the operator twice (disable → enable). This re-registers the NDI source name — known bug, temporary fix.

### Live parameters (all work while stream is running)

| Parameter | What it does | Notes |
|---|---|---|
| **Prompt** | Text description of desired output | Connect a Text COMP for live typing (see below) |
| **Seed** | Starting noise value | Keep fixed while tuning other params |
| **Step Schedule sliders** | Position of each denoising step (0–50) | Lower = more random, higher = closer to input. Keep in ascending order |
| **Guidance Scale** | Prompt adherence (like CFG) | Effective range 1.0–1.5. Above 1.5 is usually too strong |
| **Delta** | Modifier to guidance | Only active when guidance scale > 1.0 |
| **LoRA** (LoRA page) | Load a custom LoRA model | Set file path or HuggingFace ID + weight before starting stream |

**Negative prompts do not work** in StreamDiffusion — this is a known limitation of the pipeline (turbo models skip the full UNet conditioning path).

### Live prompt box setup

The prompt parameter only updates on enter/click-away. For truly live typing:

1. `Tab` → add a **Text COMP** to the network
2. Set: Type = Multi-line, Word Wrap = On, Edit Mode = Editable Continuous Update
3. Press `A` to activate the node
4. **Click and drag** the Text COMP onto the StreamDiffusionTD prompt parameter → choose **Reference**

Now typing updates the generation in real time.

### Understanding the noise → output pipeline

```
Input TOP (noise/webcam/image)
        │
        ▼
   StreamDiffusion (img2img)
   - reads each frame
   - runs denoising steps at your t_index positions
   - lower t_index = more transformation from prompt
   - higher t_index = stays closer to input
        │
        ▼
   NDI/Spout video stream
        │
        ▼
   Back into TouchDesigner as a TOP
```

Think of it as: **input image + prompt = guided hallucination of the input**. The step schedule controls how much the prompt overrides the input.

### Changing models

Stop the stream first (Settings → Stop Stream), then change the Model ID/Path and restart. Models are cached in HuggingFace's local cache after the first download.

Good models to try:
- `stabilityai/sd-turbo` — fastest, works best with 2 steps
- `KBlueLeaf/kohaku-v2.1` + LCM-LoRA — better artistic quality, needs 3–4 steps
- Any SD 1.5 compatible model via local `.safetensors` path

### Stopping

Settings page → **Stop Stream**. The command window closes.

### Advanced: OSC and other apps

The StreamDiffusionTD backend can be controlled by any OSC-compatible app, not just TouchDesigner. Set OSC ports and the video feed name on the Setup page before launching.

---

## Method B: td_bridge.py (no NDI required)

A Python script in this repo that reads the webcam, runs StreamDiffusion, and writes each output frame to `td_out/current_frame.png`. TouchDesigner polls the PNG file.

**Limitation**: PNG file polling introduces ~50–100ms extra latency and tops out at the file I/O speed, not the GPU speed. Use Method A for production work.

### Architecture

```
TouchDesigner                              Python (td_bridge.py)
─────────────                              ─────────────────────
Webcam TOP ─────────────────────────────▶ reads webcam (OpenCV)
                                                   │
OSC Out CHOP ──(127.0.0.1:9000)─────────▶ OSC listener
  /prompt "dreamlike forest"                        │
  /strength 0.7                              StreamDiffusion
  /seed 42                                          │
                                           writes PNG each frame
File In TOP ◀────(polls PNG)──────────── td_out/current_frame.png
  td_out/current_frame.png                          │
                                           OSC sender (port 9001)
OSC In CHOP ◀──(127.0.0.1:9001)──────── /fps /vram_used /status
```

### Quick Start

```powershell
# From D:\Github\StreamDiffusion with venv active:

# SD-Turbo xformers (~4.7 fps)
python td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0

# SD-Turbo TensorRT (~5.8 fps, ~53s compile first run)
python td_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam 0

# Art installation preset (7 consciousness prompts)
python td_bridge.py --config configs/consciousness_projection.yaml --webcam 0
```

Wait for: `StreamDiffusion ready. Listening on 0.0.0.0:9000`

### TouchDesigner network setup

**File In TOP**
```
File          → D:/Github/StreamDiffusion/td_out/current_frame.png
Cook          → Every Frame
Always Active → On
```

**OSC Out CHOP** (send control to Python)
```
Network Address → 127.0.0.1
Network Port    → 9000
```

**OSC In CHOP** (receive stats from Python)
```
Network Address → 127.0.0.1
Network Port    → 9001
```

### Sending prompts via OSC

```python
# In an Execute DAT:
op('oscout1').sendOSC('/prompt', ['a vast desert at golden hour, oil painting'])
op('oscout1').sendOSC('/strength', [0.7])
op('oscout1').sendOSC('/seed', [42])
```

### OSC API

**TouchDesigner → Python (port 9000)**

| Address | Type | Range | Description |
|---------|------|-------|-------------|
| `/prompt` | string | any | Generation prompt |
| `/negative` | string | any | Negative prompt (limited effect with turbo models) |
| `/strength` | float | 0.5–0.9 | img2img strength |
| `/seed` | int | any | Seed (-1 = random) |
| `/pause` | int | 0/1 | Pause/resume inference |
| `/prompt_index` | int | 0–N | Switch to preset prompt from config file |

**Python → TouchDesigner (port 9001)**

| Address | Type | Description |
|---------|------|-------------|
| `/fps` | float | Current inference FPS |
| `/vram_used` | float | GPU VRAM in GB |
| `/status` | string | `running`, `paused`, `compiling` |

### Available configs

| Config | Model | FPS (RTX 2060) | Notes |
|--------|-------|----------------|-------|
| `configs/sdturbo_fast.yaml` | SD-Turbo | 4.74 fps | Default, always works |
| `configs/sdturbo_tensorrt.yaml` | SD-Turbo | 5.83 fps | Fastest; ~53s compile first run |
| `configs/kohaku_quality.yaml` | Kohaku v2.1 | ~3.4 fps | Better artistic quality |
| `configs/consciousness_projection.yaml` | SD-Turbo | ~4.5 fps | Art installation preset |

---

## Troubleshooting (both methods)

**NDI source not showing in TD**
→ Disable and re-enable the StreamDiffusionTD operator (click X twice on the left side).

**File In TOP shows no output (Method B)**
→ Ensure `td_out/` directory exists. Check `Always Active` is On. Confirm bridge printed "StreamDiffusion ready".

**OSC messages not received**
→ Check Windows Firewall allows Python on localhost ports. Verify port numbers match.

**Webcam not found**
→ Try `--webcam 1` or `--webcam 2`. List cameras: `python -c "import cv2; [print(i, cv2.VideoCapture(i).isOpened()) for i in range(4)]"`

**First TensorRT run appears frozen**
→ Normal — compiling GPU kernels takes ~53s on RTX 2060. Check Task Manager: python.exe should show GPU usage. Engines cache to `engines/` and load in ~3s next time.

**Low VRAM**
→ TensorRT peaks at ~4.5 GB. Switch to `sdturbo_fast.yaml` (xformers, ~2.5 GB). Close browsers and other GPU apps.
