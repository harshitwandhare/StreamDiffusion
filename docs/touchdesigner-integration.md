# TouchDesigner Integration

`td_bridge.py` connects StreamDiffusion to TouchDesigner via a shared PNG file and OSC messaging.

## Architecture

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

## Quick Start

### 1. Start the Python bridge

```bash
# From the StreamDiffusion directory with venv activated:

# SD-Turbo xformers (~4.7 fps, starts immediately)
python td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0

# SD-Turbo TensorRT (~5.8 fps, ~53s compile on first run)
python td_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam 0
```

Wait for: `StreamDiffusion ready. Listening on 0.0.0.0:9000`

### 2. Set up TouchDesigner network

**File In TOP**
```
File            → D:/path/to/StreamDiffusion/td_out/current_frame.png
Cook            → Every Frame
Always Active   → On
```

**OSC In CHOP** (receive stats from Python)
```
Network Address → 127.0.0.1
Network Port    → 9001
```

**OSC Out CHOP** (send control to Python)
```
Network Address → 127.0.0.1
Network Port    → 9000
```

### 3. Send a prompt

In an Execute DAT connected to a parameter or button:

```python
import td
op('oscout1').sendOSC('/prompt', ['a vast desert at golden hour, oil painting'])
op('oscout1').sendOSC('/strength', [0.7])
```

## OSC API

### TouchDesigner → Python (port 9000)

| Address | Type | Range | Description |
|---------|------|-------|-------------|
| `/prompt` | string | any | Generation prompt |
| `/negative` | string | any | Negative prompt |
| `/strength` | float | 0.5–0.9 | img2img strength (0.5 = subtle, 0.9 = radical) |
| `/seed` | int | any | Seed (-1 for random) |
| `/pause` | int | 0/1 | Pause/resume inference |
| `/prompt_index` | int | 0–N | Switch to preset prompt from config |

### Python → TouchDesigner (port 9001)

| Address | Type | Description |
|---------|------|-------------|
| `/fps` | float | Current inference FPS |
| `/vram_used` | float | GPU VRAM usage in GB |
| `/status` | string | `running`, `paused`, `compiling` |

## Available Configs

| Config | Model | FPS (RTX 2060) | Notes |
|--------|-------|----------------|-------|
| `configs/sdturbo_fast.yaml` | SD-Turbo | 4.74 fps | Default, always works |
| `configs/sdturbo_tensorrt.yaml` | SD-Turbo | 5.83 fps | Fastest; ~53s compile first run |
| `configs/kohaku_quality.yaml` | Kohaku v2.1 | ~3.4 fps | Better artistic quality |
| `configs/consciousness_projection.yaml` | SD-Turbo | ~4.5 fps | Art installation preset |

## Troubleshooting

**File In TOP shows no output**
- Ensure `td_out/` directory exists in the StreamDiffusion folder
- Check `Always Active` is On in File In TOP
- Confirm the Python bridge printed "StreamDiffusion ready"

**OSC messages not received**
- Check Windows Firewall allows Python on localhost ports 9000/9001
- Verify OSC In CHOP Network Port matches the bridge's send port

**Webcam index not found**
- Try `--webcam 1` or `--webcam 2`
- List cameras: `python -c "import cv2; [print(i, cv2.VideoCapture(i).isOpened()) for i in range(4)]"`

**First TensorRT run is frozen**
- Normal — compiling GPU kernel library. Takes ~53s on RTX 2060. Check Task Manager for python.exe GPU usage.
- Engines cache to `engines/` and load in ~3s on subsequent runs.

**Low VRAM**
- TensorRT peaks at ~4.5 GB. Switch to `sdturbo_fast.yaml` (xformers, ~2.5 GB) if needed.
- Close hardware-accelerated browsers and other GPU apps.
