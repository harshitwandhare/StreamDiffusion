"""
td_ndi_bridge.py — StreamDiffusion → TouchDesigner via NDI video + OSC control

NDI sends the output as a proper video stream (no PNG polling).
In TouchDesigner: add an NDI In TOP, select source "StreamDiffusion".
OSC In CHOP on port 9000 receives /prompt /strength /seed /pause.
OSC Out CHOP on port 9001 sends back /fps /vram_used /status.

Usage:
    python td_ndi_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
    python td_ndi_bridge.py --config configs/sdturbo_tensorrt.yaml --webcam 0
"""

import argparse
import sys
import os
import time
import threading
import queue
import numpy as np
import cv2
import torch
from PIL import Image

# --- NDI ---
try:
    import NDIlib as ndi
    NDI_AVAILABLE = True
except ImportError:
    NDI_AVAILABLE = False
    print("[warn] ndi-python not found. Run: pip install ndi-python")

# --- OSC ---
try:
    from pythonosc import dispatcher as osc_dispatcher
    from pythonosc import osc_server
    from pythonosc.udp_client import SimpleUDPClient
    OSC_AVAILABLE = True
except ImportError:
    OSC_AVAILABLE = False
    print("[warn] python-osc not found. Run: pip install python-osc")

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.wrapper import StreamDiffusionWrapper


# ── config loader ─────────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── NDI sender ────────────────────────────────────────────────────────────────

class NDISender:
    def __init__(self, name: str = "StreamDiffusion", width: int = 512, height: int = 512):
        self.width = width
        self.height = height
        self.send = None
        if not NDI_AVAILABLE:
            return
        if not ndi.initialize():
            print("[ndi] failed to initialize NDI")
            return
        send_settings = ndi.SendCreate()
        send_settings.ndi_name = name
        self.send = ndi.send_create(send_settings)
        self.frame = ndi.VideoFrameV2()
        self.frame.FourCC = ndi.FOURCC_VIDEO_TYPE_BGRX
        self.frame.xres = width
        self.frame.yres = height
        print(f"[ndi] sending as '{name}' ({width}x{height})")

    def send_frame(self, img_rgb: np.ndarray):
        if self.send is None:
            return
        # NDI expects BGRX (4 channel)
        bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        bgrx = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
        self.frame.data = bgrx.tobytes()
        self.frame.line_stride_or_size = self.width * 4
        ndi.send_send_video_v2(self.send, self.frame)

    def close(self):
        if self.send:
            ndi.send_destroy(self.send)
            ndi.destroy()


# ── OSC layer ─────────────────────────────────────────────────────────────────

class OSCLayer:
    def __init__(self, in_port: int = 9000, out_port: int = 9001):
        self.in_port = in_port
        self.client = SimpleUDPClient("127.0.0.1", out_port) if OSC_AVAILABLE else None
        self.state = {
            "prompt": "",
            "negative": "",
            "strength": 0.75,
            "seed": 42,
            "paused": False,
        }
        self._lock = threading.Lock()

    def _set(self, key, value):
        with self._lock:
            self.state[key] = value
        print(f"[osc] {key} = {value}")

    def get_state(self) -> dict:
        with self._lock:
            return dict(self.state)

    def send_stats(self, fps: float, vram_gb: float, status: str):
        if self.client is None:
            return
        self.client.send_message("/fps", fps)
        self.client.send_message("/vram_used", vram_gb)
        self.client.send_message("/status", status)

    def start_server(self):
        if not OSC_AVAILABLE:
            return
        d = osc_dispatcher.Dispatcher()
        d.map("/prompt",   lambda addr, val: self._set("prompt", val))
        d.map("/negative", lambda addr, val: self._set("negative", val))
        d.map("/strength", lambda addr, val: self._set("strength", float(val)))
        d.map("/seed",     lambda addr, val: self._set("seed", int(val)))
        d.map("/pause",    lambda addr, val: self._set("paused", bool(int(val))))

        server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", self.in_port), d)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"[osc] listening on port {self.in_port}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/sdturbo_fast.yaml")
    parser.add_argument("--webcam", type=int, default=0)
    parser.add_argument("--osc_in",  type=int, default=9000)
    parser.add_argument("--osc_out", type=int, default=9001)
    parser.add_argument("--ndi_name", default="StreamDiffusion")
    args = parser.parse_args()

    cfg = load_config(args.config)
    width  = cfg.get("width", 512)
    height = cfg.get("height", 512)

    # ── StreamDiffusion ──────────────────────────────────────────────────────
    print(f"[sd] loading model: {cfg['model_id_or_path']}")
    stream = StreamDiffusionWrapper(
        model_id_or_path=cfg["model_id_or_path"],
        use_tiny_vae=cfg.get("use_tiny_vae", True),
        device=torch.device("cuda"),
        dtype=torch.float16,
        t_index_list=cfg.get("t_index_list", [35, 45]),
        frame_buffer_size=1,
        width=width,
        height=height,
        use_lcm_lora=cfg.get("use_lcm_lora", False),
        output_type="pil",
        warmup=10,
        acceleration=cfg.get("acceleration", "xformers"),
        mode="img2img",
        use_denoising_batch=True,
        cfg_type=cfg.get("cfg_type", "none"),
        enable_similar_image_filter=True,
        similar_image_filter_threshold=0.98,
        similar_image_filter_max_skip_frame=10,
    )

    default_prompt = cfg.get("prompts", [""])[0] if cfg.get("prompts") else cfg.get("prompt", "")
    stream.prepare(
        prompt=default_prompt,
        negative_prompt=cfg.get("negative_prompt", ""),
        num_inference_steps=50,
        guidance_scale=cfg.get("guidance_scale", 1.2),
    )
    print("[sd] warmed up")

    # ── NDI + OSC ────────────────────────────────────────────────────────────
    ndi_sender = NDISender(args.ndi_name, width, height)
    osc = OSCLayer(args.osc_in, args.osc_out)
    osc.start_server()

    # ── webcam ───────────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(args.webcam)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        print(f"[cam] webcam {args.webcam} not found. Try --webcam 1")
        return

    # ── ensure output dir for fallback PNG ───────────────────────────────────
    os.makedirs("td_out", exist_ok=True)

    print(f"\n[ready] StreamDiffusion active — NDI source: '{args.ndi_name}'")
    print("        In TouchDesigner: NDI In TOP → select 'StreamDiffusion'")
    print("        OSC control: port 9000   stats: port 9001")
    print("        Ctrl+C to stop\n")

    last_prompt = default_prompt
    fps_times: list = []

    try:
        while True:
            state = osc.get_state()

            if state["paused"]:
                osc.send_stats(0.0, 0.0, "paused")
                time.sleep(0.05)
                continue

            ret, frame_bgr = cap.read()
            if not ret:
                continue

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (width, height))
            pil_in = Image.fromarray(frame_rgb)

            # re-prepare if prompt changed
            prompt = state["prompt"] or default_prompt
            if prompt != last_prompt:
                stream.stream.prepare(prompt=prompt, num_inference_steps=50)
                last_prompt = prompt

            t0 = time.perf_counter()
            img_tensor = stream.preprocess_image(pil_in)
            out_pil: Image.Image = stream(image=img_tensor, prompt=prompt)
            dt = time.perf_counter() - t0

            # FPS smoothing
            fps_times.append(dt)
            if len(fps_times) > 30:
                fps_times.pop(0)
            fps = 1.0 / (sum(fps_times) / len(fps_times))

            vram = torch.cuda.memory_allocated() / 1e9

            # send via NDI
            out_arr = np.array(out_pil)
            ndi_sender.send_frame(out_arr)

            # fallback PNG (for File In TOP if NDI not configured)
            out_pil.save("td_out/current_frame.png")

            osc.send_stats(round(fps, 2), round(vram, 2), "running")

    except KeyboardInterrupt:
        print("\n[stop] shutting down")
    finally:
        cap.release()
        ndi_sender.close()


if __name__ == "__main__":
    main()
