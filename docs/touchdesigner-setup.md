# TouchDesigner + StreamDiffusion — Setup Guide

Real-time diffusion in TouchDesigner: webcam in → AI transform → live output,
with prompt control, strength/noise, and model switching from TD.

---

## How it works

```
Webcam
  |
  v
Python: td_bridge.py  (GPU inference on RTX 2060, ~4.1 fps)
  |-- writes --> td_out/input_frame.png    raw webcam (before diffusion)
  |-- writes --> td_out/output_frame.png   diffused output
  |
  <-- OSC port 9000  TD sends:  /prompt  /strength  /seed  /model  /pause
  --> OSC port 9001  TD gets:   /fps  /vram_used  /status  /model_name
```

---

## Step 1 — Start the Python backend

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

Wait for:
```
[INIT] Model ready.
[RUN] Streaming.
      Model:  sdturbo_fast
      Frames: input_frame.png  |  output_frame.png  |  current_frame.png
      OSC in: port 9000   out: port 9001
```

A Python preview window opens (input left, output right). Leave this terminal running.

To hide the Python window and save a bit of GPU:
```powershell
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0 --no-window
```

---

## Step 2 — Build the TD network (4 nodes, ~2 minutes)

Open **TouchDesigner 2023** → File → New Project.

### Node 1: Output image display

`Tab` → click **TOP** tab → click **File In** → place it

In the **Parameters panel** (right side):
- **File** → `D:/Github/StreamDiffusion/td_out/output_frame.png`  
  *(forward slashes required)*
- **Cook Rate** → `Every Frame`
- **Always Active** → `On` (checkbox)

Right-click the node → **View** → live diffused frames appear.

### Node 2: OSC Out (TD → Python, sends controls)

`Tab` → click **CHOP** tab → click **OSC Out** → place it

Parameters:
- **Network Address** → `127.0.0.1`
- **Network Port** → `9000`

TD names this `oscout1` by default.

### Node 3: OSC In (Python → TD, receives stats)

`Tab` → click **CHOP** tab → click **OSC In** → place it

Parameters:
- **Network Port** → `9001`
- **Active** → `On`

After a second: `/fps`, `/vram_used`, `/status`, `/model_name` channels appear.

### Node 4: Control DAT (prompt + strength + model)

`Tab` → click **DAT** tab → click **Text** → place it

Double-click to open → paste this exactly:

```python
# StreamDiffusion control — edit values below, then right-click -> Run Script

osc = op('oscout1')   # matches the default OSC Out node name

# --- edit these ---
prompt   = "vivid oil painting, golden hour, cinematic"
strength = 0.6    # 0.0 = subtle, 1.0 = full transform
seed     = 42
# ------------------

osc.sendOSC('/prompt',   [prompt])
osc.sendOSC('/strength', [strength])
osc.sendOSC('/seed',     [seed])
```

To use: edit the prompt or strength → right-click the Text DAT node → **Run Script**.  
Python receives it and the output updates within 1–2 frames.

---

## Step 3 — Model switching

Create one Text DAT per model. Paste, then right-click → **Run Script** to switch.

**SD-Turbo — fast (~4.1 fps, 2.5 GB)**
```python
op('oscout1').sendOSC('/model', ['configs/sdturbo_fast.yaml'])
```

**Kohaku — quality (~3.4 fps, 2.7 GB)**
```python
op('oscout1').sendOSC('/model', ['configs/kohaku_quality.yaml'])
```

**Art install — 7 preset prompts (~4.1 fps, 2.5 GB)**
```python
op('oscout1').sendOSC('/model', ['configs/consciousness_projection.yaml'])
```

**TensorRT — fastest (~5.6 fps, 4.5 GB)**
```python
op('oscout1').sendOSC('/model', ['configs/sdturbo_tensorrt.yaml'])
```

After running: terminal shows `[OSC] model switch requested` → model reloads (~20s) →
output resumes automatically. No need to restart the script.

---

## Step 4 — Art installation presets

After switching to the art config, cycle through 7 built-in prompts. One Text DAT per preset:

```python
op('oscout1').sendOSC('/prompt_index', [0])   # vivid digital painting
op('oscout1').sendOSC('/prompt_index', [1])   # cosmic consciousness
op('oscout1').sendOSC('/prompt_index', [2])   # fractal dreamscape
op('oscout1').sendOSC('/prompt_index', [3])   # bioluminescent deep sea
op('oscout1').sendOSC('/prompt_index', [4])   # sacred geometry projection
op('oscout1').sendOSC('/prompt_index', [5])   # neural lattice visualization
op('oscout1').sendOSC('/prompt_index', [6])   # quantum field interference
```

---

## Step 5 — Also show the raw input (optional)

Add a second **File In TOP**:
- **File** → `D:/Github/StreamDiffusion/td_out/input_frame.png`
- **Cook Rate** → `Every Frame`
- **Always Active** → `On`

Place it next to the output TOP. You now have input on the left, diffused output on the right.

---

## All OSC commands reference

Send any of these from a Text DAT → right-click → Run Script:

```python
osc = op('oscout1')

osc.sendOSC('/prompt',       ["your prompt text here"])
osc.sendOSC('/negative',     ["blurry, low quality"])   # negative prompt
osc.sendOSC('/strength',     [0.6])     # 0.0–1.0
osc.sendOSC('/seed',         [42])      # any integer
osc.sendOSC('/pause',        [1])       # 1 = pause
osc.sendOSC('/pause',        [0])       # 0 = resume
osc.sendOSC('/prompt_index', [3])       # art preset 0–6
osc.sendOSC('/model',        ['configs/kohaku_quality.yaml'])  # hot-swap model
```

Incoming (visible in OSC In CHOP after Python sends them):
```
/fps             current generation fps
/vram_used       VRAM in MB
/status          "running" / "warmup" / "loading" / "paused"
/model_name      current config name (e.g. sdturbo_fast)
/prompt_current  first 80 chars of the active prompt
```

---

## Configs reference

| Config | Model | Steps | FPS | VRAM | Notes |
|---|---|---|---|---|---|
| `configs/sdturbo_fast.yaml` | SD-Turbo (local) | 2 | **4.14** | 2.5 GB | Default, always works |
| `configs/sdturbo_tensorrt.yaml` | SD-Turbo + TRT | 2 | **5.59** | 4.5 GB | ~53s compile first run |
| `configs/kohaku_quality.yaml` | Kohaku v2.1 + LCM-LoRA | 3 | **~3.4** | 2.7 GB | Better artistic quality |
| `configs/consciousness_projection.yaml` | SD-Turbo (local) | 2 | **~4.1** | 2.5 GB | Art mode, 7 presets |

---

## Common issues

| Problem | Fix |
|---|---|
| Black frame in File In TOP | Cook Rate = `Every Frame`, Always Active = `On` |
| File In TOP not updating | Path must use forward slashes: `D:/Github/...` not `D:\Github\...` |
| OSC Run Script does nothing | Check OSC Out node name is `oscout1` — if you renamed it, update the script |
| OSC not reaching Python | Check terminal shows `[OSC] Listening on 127.0.0.1:9000` |
| `/model` switch not working | Terminal must show `[OSC] model switch requested` — takes ~20s to reload |
| OSC In CHOP empty | Port = `9001`, Active = `On`; Python must be running |
| Webcam error -1072875772 | Cosmetic MSMF warning — camera still works fine |
| Python preview window missing | Run without `--no-window`, or just ignore — doesn't affect TD |
