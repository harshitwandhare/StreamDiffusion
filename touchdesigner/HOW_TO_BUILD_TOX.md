# How to Build the StreamDiffusionTD Component

This creates a reusable `.tox` operator in TouchDesigner — same concept as
the dotsimulate one, but free and built on our own backend.

---

## One-time build (takes ~2 minutes)

### Step 1 — Start the NDI bridge first

In a terminal (with venv active):
```
python td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
```
Wait for: `[ready] StreamDiffusion active`

### Step 2 — Open TouchDesigner 2023

Open a new empty project.

### Step 3 — Create a Text DAT

Press `Tab` → search **Text DAT** → place it.

### Step 4 — Paste the builder script

Open `touchdesigner/build_component.py` from this repo.
Select all, copy, paste into the Text DAT.

### Step 5 — Run the script

Right-click the Text DAT → **Run Script**.

A `StreamDiffusionTD` Container COMP appears in your network.

### Step 6 — Configure

Click the component. On the **Setup page**:
- **Base Folder** → `D:\Github\StreamDiffusion`
- **Config** → pick a preset
- **Webcam** → your camera index

### Step 7 — Start

Click **▶ Start Stream** on the Setup page.

Watch the **Info page** — Status changes to `running` and FPS appears.

### Step 8 — Wire it up

The component has an `OUT` TOP (NDI In TOP inside). Connect it like any TOP:

```
[StreamDiffusionTD] OUT ──▶ [Composite TOP] ──▶ [your output]
```

Connect any image source as additional input to drive the img2img:
```
[Noise TOP] ──▶ [StreamDiffusionTD] (change Config strength to taste)
[Webcam TOP] ──▶ [StreamDiffusionTD]
[Movie File In TOP] ──▶ [StreamDiffusionTD]
```

### Step 9 — Save as .tox

Right-click `StreamDiffusionTD` → **Save Component As...** → `StreamDiffusionTD.tox`

Drop this `.tox` into any future project — no rebuild needed.

---

## Live controls (while stream is running)

All of these update in real time:

| Parameter | Where | Effect |
|---|---|---|
| Prompt | Settings page | Type anything — updates generation immediately |
| Strength | Settings page | 0.3 = subtle, 0.9 = radical transformation |
| Guidance Scale | Settings page | 1.0–1.5 sweet spot |
| Seed | Settings page | Fix it while tuning other params |
| Stop Stream | Setup page | Shuts down Python bridge |

**For a live prompt text box** (updates as you type):
1. Add a **Text COMP** → Type: Multi-line, Edit Mode: Editable Continuous Update
2. Drag it onto the component's **Prompt** parameter → choose **Reference**

**Drive parameters from audio/CHOP:**
Drag any CHOP channel onto Strength, Seed, etc. → choose **Export**.

---

## What's inside the component

```
StreamDiffusionTD (Container COMP)
├── ndi_in (NDI In TOP)          ← receives video from Python bridge
├── OUT    (Null TOP)             ← your output connection point
├── osc_in  (OSC In CHOP)        ← receives /fps /vram_used /status
├── osc_out (OSC Out CHOP)       ← sends /prompt /strength /seed /pause
├── controller (Script DAT)      ← launches/stops subprocess, reads stdout
├── param_executor (Execute DAT) ← fires OSC on parameter changes
└── README (Text DAT)            ← quick reference
```

---

## Troubleshooting

**Status stays "starting..." and never reaches "running"**
→ Check that Base Folder points to the StreamDiffusion install with `.venv/` inside.
→ Open the TouchDesigner Textport (Alt+T) — `[SD]` lines show the bridge output.

**NDI In TOP shows no source**
→ Make sure `td_ndi_bridge.py` is running first (check the terminal).
→ Try clicking the Source Name dropdown in the NDI In TOP — "StreamDiffusion" should appear.

**TensorRT config looks frozen on first run**
→ Normal. GPU kernel compilation takes ~53s. Watch Task Manager — python.exe shows GPU usage.

**Low FPS**
→ Switch Config to `sdturbo_fast` (xformers). Close browsers and GPU apps.
→ TensorRT gives +23% on RTX 2060, larger gains on RTX 3000/4000.
