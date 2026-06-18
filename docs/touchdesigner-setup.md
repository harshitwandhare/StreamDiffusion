# TouchDesigner + StreamDiffusion — Complete Setup Guide

This guide covers how to build the full interactive interface: live webcam input, diffused output,
prompt text box, strength slider, model switching, and art presets — all controllable from TouchDesigner.

---

## How it works

```
Webcam
  |
  v
Python: td_bridge.py  (GPU inference, ~4.8 fps)
  |-- writes --> td_out/input_frame.png   (raw webcam, for TD left panel)
  |-- writes --> td_out/output_frame.png  (diffused output, for TD right panel)
  |
  <-- OSC port 9000 --  TouchDesigner sends: /prompt /strength /seed /model /pause
  --> OSC port 9001 --> TouchDesigner gets:  /fps /vram_used /status /model_name /prompt_current
```

---

## Step 1: Start the Python backend

Open a PowerShell terminal. Activate the venv and start the bridge:

```powershell
cd D:\Github\StreamDiffusion
.venv\Scripts\activate
python touchdesigner/td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```

Wait for:
```
[INIT] Model ready.
[RUN] Streaming. Ctrl+C to stop.
      Model:  sdturbo_fast
      Output: td_out/
      Frames: input_frame.png  |  output_frame.png  |  current_frame.png
      OSC in: port 9000   out: port 9001
```

A preview window opens showing **input | output** side-by-side with FPS overlaid.
Leave this terminal running throughout the session.

---

## Step 2: Open TouchDesigner and build the network

Open **TouchDesigner 2023**. File → New Project.

### Option A — Auto-build (recommended, ~30 seconds)

1. Press `Tab` → search `Text DAT` → place one anywhere
2. Double-click the Text DAT to open it
3. Select all text (Ctrl+A), delete it
4. Open `touchdesigner/td_network_builder.py` in a text editor, copy the entire contents
5. Paste into the Text DAT
6. Right-click the Text DAT → **Run Script**
7. The full network is created in a **`/StreamDiffusion`** container

### Option B — Manual build (understand every node)

Follow all the steps in the **Manual build** section below.

---

## Step 3: Make the output visible

After the auto-build (or manual build):

1. Open the `/StreamDiffusion` container (double-click it)
2. Find **`input_view`** TOP and **`output_view`** TOP
3. For each: right-click → **View** to open the viewer
4. You should see:
   - **input_view**: raw webcam frames updating live
   - **output_view**: diffused/styled frames updating live

If the images are static or black:
- Click `input_view` → Parameters → set **Cook Rate** = `Every Frame`, **Always Active** = `On`
- Same for `output_view`

---

## Step 4: Change the prompt live

Two ways:

**From the Text DAT:**
1. In the `/StreamDiffusion` container, double-click **`prompt_text`** DAT
2. Edit the text → the **executor** DAT detects the change and sends `/prompt` via OSC automatically
3. The Python backend receives it and updates generation within 1-2 frames

**Run manually:**
1. Double-click `sender` DAT → uncomment/call `send_prompt()`
2. Right-click → Run Script

---

## Step 5: Adjust transformation strength

1. Double-click **`strength_text`** DAT
2. Change the value (e.g. `0.3` = subtle, `0.8` = heavy transform)
3. The executor DAT auto-sends `/strength` to Python

Range: `0.0` (no change, output = input) to `1.0` (full diffusion, ignores input)
Sweet spot for webcam: `0.45`–`0.65`

---

## Step 6: Switch models

Right-click any model-switch DAT → **Run Script**:

| DAT name | Model | FPS | VRAM | Notes |
|---|---|---|---|---|
| `switch_sdturbo` | SD-Turbo (local) | 4.8 | 2.5 GB | Default, fastest |
| `switch_kohaku` | Kohaku v2.1 + LCM-LoRA | 3.4 | 2.7 GB | Better artistic quality |
| `switch_art` | SD-Turbo (consciousness) | 4.5 | 2.5 GB | 7 built-in art prompts |
| `switch_tensorrt` | SD-Turbo + TensorRT | 5.8 | 4.5 GB | Fastest, ~53s compile |

After clicking:
- Terminal shows `[OSC] model switch requested`
- Status changes to `loading` (~20 seconds for model reload)
- Output freezes on last frame, then resumes with new model
- `stats_text` DAT updates with new model name

---

## Step 7: Art installation presets (consciousness_projection config)

After switching to `switch_art`:

Right-click any `preset_0` through `preset_6` → **Run Script** to cycle through 7 built-in prompts:

| Preset | Prompt style |
|---|---|
| 0 | Default (vivid digital painting) |
| 1 | Cosmic consciousness |
| 2 | Fractal dreamscape |
| 3 | Bioluminescent deep sea |
| 4 | Sacred geometry projection |
| 5 | Neural lattice visualization |
| 6 | Quantum field interference |

---

## Step 8: Live stats readout

The **`stats_text`** DAT updates every cook cycle with:

```
FPS     4.7
VRAM    2495 MB
Status  running
Model   sdturbo_fast
Prompt  vivid digital painting, dynamic lighting...
```

To display this in TD's viewport:
1. `Tab` → **Table TOP** → connect `stats_text` DAT → renders as a text overlay
2. Or: `Tab` → **Text TOP** → set the text source to `op('stats_text')[0, 0]`

---

## Manual build (complete node list)

If the auto-build script doesn't work on your TD version, here's every node to create manually:

### A. Output display

1. `Tab` → **File In TOP** → name it `input_view`
   - File: `D:/Github/StreamDiffusion/td_out/input_frame.png`
   - Cook Rate: `Every Frame`
   - Always Active: `On`

2. `Tab` → **File In TOP** → name it `output_view`
   - File: `D:/Github/StreamDiffusion/td_out/output_frame.png`
   - Cook Rate: `Every Frame`
   - Always Active: `On`

### B. OSC communication

3. `Tab` → **OSC In CHOP** → name it `osc_in`
   - Port: `9001`
   - Active: On
   - Channels appear: `/fps`, `/vram_used`, `/status`, `/model_name`, `/prompt_current`

4. `Tab` → **OSC Out CHOP** → name it `osc_out`
   - Network Address: `127.0.0.1`
   - Network Port: `9000`

### C. Controls

5. `Tab` → **Text DAT** → name it `prompt_text`
   - Double-click → type your prompt
   - (The executor DAT below auto-sends it)

6. `Tab` → **Text DAT** → name it `strength_text`
   - Contents: `0.5`

7. `Tab` → **Text DAT** → name it `seed_text`
   - Contents: `42`

### D. Controller (auto-sends OSC when controls change)

8. `Tab` → **DAT Execute DAT** → name it `executor`
   - Open it → paste:
     ```python
     def onTableChange(dat):
         osc = op('osc_out')
         if dat.name == 'prompt_text':
             txt = dat[0, 0].val.strip()
             if txt:
                 osc.sendOSC('/prompt', [txt])
         elif dat.name == 'strength_text':
             try:
                 osc.sendOSC('/strength', [max(0.0, min(1.0, float(dat[0, 0].val)))])
             except Exception:
                 pass
         elif dat.name == 'seed_text':
             try:
                 osc.sendOSC('/seed', [int(dat[0, 0].val)])
             except Exception:
                 pass
     ```
   - Parameters → DATs field: `prompt_text strength_text seed_text`

### E. Model-switch DATs (right-click → Run Script to use)

9. Create four **Text DATs**, one per model:

```python
# switch_sdturbo
op('osc_out').sendOSC('/model', ['configs/sdturbo_fast.yaml'])
```
```python
# switch_kohaku
op('osc_out').sendOSC('/model', ['configs/kohaku_quality.yaml'])
```
```python
# switch_art
op('osc_out').sendOSC('/model', ['configs/consciousness_projection.yaml'])
```
```python
# switch_tensorrt
op('osc_out').sendOSC('/model', ['configs/sdturbo_tensorrt.yaml'])
```

### F. Preset DATs (for art mode)

Create seven **Text DATs** named `preset_0` through `preset_6`:
```python
# preset_0
op('osc_out').sendOSC('/prompt_index', [0])
# preset_1
op('osc_out').sendOSC('/prompt_index', [1])
# ... etc up to preset_6
```

---

## Adding a noise layer in TD

The Python backend transforms the webcam image using the prompt as a guide.
To add controllable noise before it reaches Python:

1. `Tab` → **Noise TOP** → parameters:
   - Type: `Sparse`
   - Period: `0.5`
   - Amplitude: `0.3`
2. `Tab` → **Composite TOP** → connect `noise` + `input_view` → set Operation: `Add`
3. Save the composite to `td_out/input_override.png` via **Movie File Out TOP**

Alternatively, just increase `strength_text` — higher values make the diffusion
more aggressive and add visual noise to the output.

---

## Using an image file instead of webcam

To use a static image instead of webcam as input:

Stop td_bridge.py (Ctrl+C) and add `--input` flag:
```powershell
# Not supported natively in td_bridge.py — use img2img example instead:
python examples/img2img/single.py `
  --model_id_or_path "D:\Github\StreamDiffusion\models\sd-turbo" `
  --prompt "oil painting, warm tones" `
  --acceleration xformers `
  --cfg_type none
```

For live image-to-image from a TD-driven source instead of a webcam, edit `td_bridge.py`
and change `cv2.VideoCapture(self.webcam_id)` to read from a shared folder instead.

---

## Common issues

| Problem | Fix |
|---|---|
| Black frame in output_view | Check Cook Rate = Every Frame, Always Active = On |
| OSC not received by Python | Confirm td_bridge.py shows `[OSC] Listening on 127.0.0.1:9000` |
| Model switch does nothing | Check terminal shows `[OSC] model switch requested` — may take 20s |
| Stats DAT empty | Check osc_in CHOP port = 9001, Active = On |
| executor DAT not firing | Check Parameters → DATs field lists `prompt_text strength_text seed_text` |
| td_network_builder.py errors | Your TD version may not support `oscInCHOP` — use manual build |
| Webcam error -1072875772 | Normal MSMF warning — camera still works, just cosmetic |
