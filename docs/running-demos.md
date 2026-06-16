# Running the Demos

All demos require the venv to be active. From `D:\Github\StreamDiffusion`:

```powershell
.venv\Scripts\activate
```

Run `python test_cuda.py` first to confirm your environment is healthy.

---

## 1. Real-time img2img (webcam in browser)

The main demo. Streams your webcam through StreamDiffusion and shows the output in a browser.

```powershell
cd demo/realtime-img2img
python main.py --port 8080 --acceleration xformers
```

Open `http://localhost:8080`. Allow camera access. Type a prompt and watch it apply in real time.

**With TensorRT (~23% faster, first run compiles ~53s):**
```powershell
python main.py --port 8080 --acceleration tensorrt
```

**Use a local model instead of downloading:**
```powershell
$env:SD_MODEL = "D:\Github\StreamDiffusion\models\sd-turbo"
python main.py --port 8080
```

---

## 2. Real-time txt2img (pure text to image, no webcam)

Generates images from a text prompt only. No camera needed.

```powershell
cd demo/realtime-txt2img
python main.py --port 8080
```

Open `http://localhost:8080`. Type a prompt, hit enter, watch it generate continuously.

---

## 3. vid2vid (video file input)

Applies the diffusion pipeline to a video file frame by frame.

```powershell
cd demo/vid2vid
python main.py --port 8080
```

Open `http://localhost:8080`. Upload a video file. The processed stream appears alongside.

---

## 4. TouchDesigner integration

Two approaches — choose based on what you need:

| Approach | Quality | Setup | Best for |
|---|---|---|---|
| **StreamDiffusionTD .tox** (recommended) | High — NDI/Spout video | Download .tox, install NDI SDK | Full TD-native workflow, model switching, LoRA |
| **td_bridge.py** (this repo) | Basic — shared PNG file | Just run the script | Quick test, no extra installs |

See [`docs/touchdesigner-integration.md`](touchdesigner-integration.md) for both workflows.

---

## 5. Standalone benchmark (no webcam, no browser)

Measures raw inference FPS on your GPU.

```powershell
# xformers
python research_benchmark.py --quick

# TensorRT
python run_tensorrt_benchmark.py
```

Results saved to `reports/benchmark_<timestamp>.md`.

---

## Parameter reference (all web demos)

| Parameter | Effect | Recommended starting point |
|---|---|---|
| Prompt | Text description of the output | Start simple, one adjective at a time |
| Steps / t_index_list | How many denoising steps; more = slower but better | 2 steps for real-time, 4 for quality |
| Strength | How far from the input the output can drift | 0.5 = subtle, 0.9 = radical change |
| Guidance scale | Prompt adherence multiplier | 1.0–1.2 (above 1.5 is usually too strong) |
| Seed | Locks the random starting noise | Keep fixed while tuning other params |
| Similar image filter | Skips frames that are nearly identical to the last | Useful with noisy webcam inputs |

---

## Stopping any demo

`Ctrl+C` in the terminal. The browser tab can be closed at any time — the Python process keeps running until you stop it.
