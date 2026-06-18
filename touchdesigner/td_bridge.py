"""
td_bridge.py — StreamDiffusion TouchDesigner Integration Bridge
===============================================================
Connects StreamDiffusion to TouchDesigner via:
  - Input:  webcam / screen capture (OpenCV)
  - Control: OSC messages from TouchDesigner (port 9000)
  - Output: frame folder watched by TD + optional display window

OSC messages this script accepts (from TouchDesigner):
  /prompt <string>          — swap prompt on next frame
  /negative <string>        — update negative prompt
  /strength <float 0-1>     — delta (how much to transform input)
  /seed <int>               — change seed
  /pause <int>              — 1 = pause, 0 = resume
  /prompt_index <int>       — switch to library prompt by index
  /model <string>           — hot-swap config file path (e.g. "configs/kohaku_quality.yaml")

OSC messages sent back to TouchDesigner (port 9001):
  /fps <float>              — current generation fps
  /vram_used <float>        — VRAM used in MB
  /status <string>          — "running" / "warmup" / "paused" / "loading"
  /model_name <string>      — current model short name
  /prompt_current <string>  — current active prompt

Saved frames (TouchDesigner watches these):
  td_out/input_frame.png    — raw webcam input (before diffusion)
  td_out/output_frame.png   — diffused output
  td_out/current_frame.png  — alias for output_frame.png (compat)

Usage:
  python td_bridge.py --config configs/sdturbo_fast.yaml
  python td_bridge.py --config configs/sdturbo_fast.yaml --webcam 0
  python td_bridge.py --config configs/kohaku_quality.yaml --no-window
"""

import os
import sys
import time
import threading
import argparse
from pathlib import Path

import torch
import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.wrapper import StreamDiffusionWrapper

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    print("[WARNING] OpenCV not found. Install with: pip install opencv-python")

try:
    from pythonosc import dispatcher as osc_dispatcher
    from pythonosc import osc_server
    from pythonosc.udp_client import SimpleUDPClient
    OSC_AVAILABLE = True
except ImportError:
    OSC_AVAILABLE = False
    print("[WARNING] python-osc not found. Install with: pip install python-osc")

from PIL import Image


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        return yaml.safe_load(f)


class StreamBridge:
    """
    Real-time StreamDiffusion bridge for TouchDesigner integration.
    Handles webcam input, OSC control, and frame output.
    """

    def __init__(self, config: dict, config_path: str, webcam_id: int = 0, show_window: bool = True):
        self.cfg = config
        self.config_path = config_path
        self.webcam_id = webcam_id
        self.show_window = show_window and OPENCV_AVAILABLE

        self._lock = threading.Lock()
        self._current_prompt = config["prompts"]["default"]
        self._negative_prompt = config["prompts"].get("negative", "")
        self._delta = config["inference"].get("delta", 0.5)
        self._seed = config["inference"].get("seed", 42)
        self._paused = False
        self._prompt_library = config["prompts"].get("library", [])
        self._prompt_dirty = False

        # Model hot-swap
        self._pending_config_path = None
        self._model_name = Path(config_path).stem

        self._fps = 0.0
        self._frame_count = 0
        self._status = "initializing"

        self.output_dir = Path(config["output"].get("frame_dir", "td_out"))
        self.output_dir.mkdir(exist_ok=True)
        self.save_frames = config["output"].get("save_frames", True)

        self.stream = None
        self.osc_client = None
        self._stop_event = threading.Event()

        # Last output kept while model reloads
        self._last_output_pil = None

    # -------------------------------------------------------------------------
    # OSC handlers
    # -------------------------------------------------------------------------

    def _osc_prompt(self, address, *args):
        if args:
            with self._lock:
                self._current_prompt = str(args[0])
                self._prompt_dirty = True
            print(f"\n[OSC] prompt -> {self._current_prompt[:60]}")

    def _osc_negative(self, address, *args):
        if args:
            with self._lock:
                self._negative_prompt = str(args[0])
                self._prompt_dirty = True
            print(f"\n[OSC] negative -> {self._negative_prompt[:60]}")

    def _osc_strength(self, address, *args):
        if args:
            with self._lock:
                self._delta = float(max(0.0, min(1.0, args[0])))
                self._prompt_dirty = True
            print(f"\n[OSC] strength -> {self._delta:.2f}")

    def _osc_seed(self, address, *args):
        if args:
            with self._lock:
                self._seed = int(args[0])
                self._prompt_dirty = True
            print(f"\n[OSC] seed -> {self._seed}")

    def _osc_pause(self, address, *args):
        val = int(args[0]) if args else -1
        with self._lock:
            self._paused = bool(val) if val >= 0 else not self._paused
        print(f"\n[OSC] {'paused' if self._paused else 'resumed'}")

    def _osc_prompt_index(self, address, *args):
        if args and self._prompt_library:
            idx = int(args[0]) % len(self._prompt_library)
            with self._lock:
                self._current_prompt = self._prompt_library[idx]
                self._prompt_dirty = True
            print(f"\n[OSC] prompt_index {idx} -> {self._current_prompt[:60]}")

    def _osc_model(self, address, *args):
        """Hot-swap the model by loading a new config file. Takes ~20s to reload."""
        if args:
            cfg_path = str(args[0]).strip()
            # Resolve relative to repo root
            if not os.path.isabs(cfg_path):
                repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cfg_path = os.path.join(repo_root, cfg_path)
            if os.path.exists(cfg_path):
                with self._lock:
                    self._pending_config_path = cfg_path
                print(f"\n[OSC] model switch requested -> {cfg_path}")
            else:
                print(f"\n[OSC] model config not found: {cfg_path}")

    # -------------------------------------------------------------------------
    # OSC server setup
    # -------------------------------------------------------------------------

    def _start_osc_server(self):
        if not OSC_AVAILABLE:
            return

        osc_cfg = self.cfg.get("osc", {})
        host = osc_cfg.get("host", "127.0.0.1")
        in_port = osc_cfg.get("in_port", 9000)
        out_port = osc_cfg.get("out_port", 9001)

        try:
            self.osc_client = SimpleUDPClient(host, out_port)
        except Exception as e:
            print(f"[OSC] Client init failed: {e}")

        d = osc_dispatcher.Dispatcher()
        d.map("/prompt", self._osc_prompt)
        d.map("/negative", self._osc_negative)
        d.map("/strength", self._osc_strength)
        d.map("/seed", self._osc_seed)
        d.map("/pause", self._osc_pause)
        d.map("/prompt_index", self._osc_prompt_index)
        d.map("/model", self._osc_model)

        try:
            server = osc_server.ThreadingOSCUDPServer((host, in_port), d)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            print(f"[OSC] Listening on {host}:{in_port}, sending to {host}:{out_port}")
        except Exception as e:
            print(f"[OSC] Server init failed (port {in_port} in use?): {e}")

    # -------------------------------------------------------------------------
    # Model initialization
    # -------------------------------------------------------------------------

    def _init_stream(self, cfg=None):
        if cfg is None:
            cfg = self.cfg
        m = cfg["model"]
        inf = cfg["inference"]

        print(f"\n[INIT] Loading model: {m['id']}")
        print(f"[INIT] Acceleration: {inf.get('acceleration', 'xformers')}")
        self._status = "loading"
        self._send_osc_stats()

        if self.stream is not None:
            del self.stream
            torch.cuda.empty_cache()

        self.stream = StreamDiffusionWrapper(
            model_id_or_path=m["id"],
            use_tiny_vae=m.get("use_tiny_vae", True),
            use_lcm_lora=m.get("use_lcm_lora", False),
            t_index_list=inf["t_index_list"],
            frame_buffer_size=1,
            width=inf.get("width", 512),
            height=inf.get("height", 512),
            warmup=inf.get("warmup", 10),
            acceleration=inf.get("acceleration", "xformers"),
            mode=inf.get("mode", "img2img"),
            use_denoising_batch=True,
            cfg_type=inf.get("cfg_type", "none"),
            seed=self._seed,
            enable_similar_image_filter=inf.get("enable_similar_image_filter", False),
            similar_image_filter_threshold=inf.get("similar_image_filter_threshold", 0.98),
            use_safety_checker=False,
        )

        self.stream.prepare(
            prompt=self._current_prompt,
            negative_prompt=self._negative_prompt,
            num_inference_steps=inf.get("num_inference_steps", 50),
            guidance_scale=inf.get("guidance_scale", 1.0),
            delta=self._delta,
        )
        print("[INIT] Model ready.")
        self._status = "warmup"

    def _send_osc_stats(self):
        if not (OSC_AVAILABLE and self.osc_client):
            return
        try:
            vram_mb = torch.cuda.memory_allocated() / 1024**2
            self.osc_client.send_message("/fps", float(self._fps))
            self.osc_client.send_message("/vram_used", float(vram_mb))
            self.osc_client.send_message("/status", str(self._status))
            self.osc_client.send_message("/model_name", str(self._model_name))
            self.osc_client.send_message("/prompt_current", str(self._current_prompt[:80]))
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Main inference loop
    # -------------------------------------------------------------------------

    def run(self):
        self._init_stream()
        self._start_osc_server()

        if not OPENCV_AVAILABLE:
            print("[ERROR] OpenCV required for webcam input.")
            return

        cap = cv2.VideoCapture(self.webcam_id)
        if not cap.isOpened():
            print(f"[ERROR] Cannot open webcam {self.webcam_id}")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg["inference"].get("width", 512))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg["inference"].get("height", 512))

        print(f"\n[RUN] Streaming. Ctrl+C to stop.")
        print(f"      Model:  {self._model_name}")
        print(f"      Input:  webcam {self.webcam_id}")
        print(f"      Output: {self.output_dir}/")
        print(f"      Frames: input_frame.png  |  output_frame.png  |  current_frame.png")
        if OSC_AVAILABLE:
            osc_cfg = self.cfg.get("osc", {})
            print(f"      OSC in: port {osc_cfg.get('in_port', 9000)}   out: port {osc_cfg.get('out_port', 9001)}")
        print()

        fps_timer = time.perf_counter()
        fps_frames = 0
        send_stats_timer = time.perf_counter()

        try:
            while not self._stop_event.is_set():

                # -- Model hot-swap check --
                with self._lock:
                    pending_cfg = self._pending_config_path
                    self._pending_config_path = None

                if pending_cfg:
                    try:
                        new_cfg = load_config(pending_cfg)
                        self.cfg = new_cfg
                        self._model_name = Path(pending_cfg).stem
                        with self._lock:
                            self._current_prompt = new_cfg["prompts"]["default"]
                            self._negative_prompt = new_cfg["prompts"].get("negative", "")
                            self._delta = new_cfg["inference"].get("delta", 0.5)
                            self._prompt_dirty = False
                        self._init_stream(new_cfg)
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, new_cfg["inference"].get("width", 512))
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, new_cfg["inference"].get("height", 512))
                    except Exception as e:
                        print(f"[ERROR] Model swap failed: {e}")

                ret, frame_bgr = cap.read()
                if not ret:
                    continue

                with self._lock:
                    paused = self._paused
                    dirty = self._prompt_dirty
                    prompt = self._current_prompt
                    neg = self._negative_prompt
                    delta = self._delta

                if paused:
                    time.sleep(0.05)
                    continue

                if dirty:
                    inf = self.cfg["inference"]
                    self.stream.prepare(
                        prompt=prompt,
                        negative_prompt=neg,
                        num_inference_steps=inf.get("num_inference_steps", 50),
                        guidance_scale=inf.get("guidance_scale", 1.0),
                        delta=delta,
                    )
                    with self._lock:
                        self._prompt_dirty = False
                    self._status = "running"

                w = self.cfg["inference"].get("width", 512)
                h = self.cfg["inference"].get("height", 512)
                frame_bgr_resized = cv2.resize(frame_bgr, (w, h))
                frame_rgb = cv2.cvtColor(frame_bgr_resized, cv2.COLOR_BGR2RGB)
                input_pil = Image.fromarray(frame_rgb)

                # Save raw input frame for TD side-by-side view
                if self.save_frames:
                    input_pil.save(str(self.output_dir / "input_frame.png"))

                image_tensor = self.stream.preprocess_image(input_pil)
                output_pil = self.stream(image=image_tensor)

                if output_pil is None:
                    continue

                self._last_output_pil = output_pil
                self._frame_count += 1
                fps_frames += 1
                self._status = "running"

                now = time.perf_counter()
                elapsed = now - fps_timer
                if elapsed >= 1.0:
                    self._fps = fps_frames / elapsed
                    fps_frames = 0
                    fps_timer = now
                    print(f"\r[FPS] {self._fps:.1f}  VRAM: {torch.cuda.memory_allocated()/1024**2:.0f}MB  [{self._model_name}]  {prompt[:40]}...", end="", flush=True)

                if self.save_frames:
                    output_pil.save(str(self.output_dir / "output_frame.png"))
                    output_pil.save(str(self.output_dir / "current_frame.png"))

                if self.show_window:
                    out_np = np.array(output_pil)
                    out_bgr = cv2.cvtColor(out_np, cv2.COLOR_RGB2BGR)
                    # Side-by-side: input | output
                    side = np.concatenate([frame_bgr_resized, out_bgr], axis=1)
                    cv2.putText(side, f"{self._fps:.1f} fps  [{self._model_name}]  {prompt[:35]}", (8, 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    cv2.imshow("StreamDiffusion — input | output", side)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                if OSC_AVAILABLE and self.osc_client and now - send_stats_timer >= 0.5:
                    send_stats_timer = now
                    self._send_osc_stats()

        except KeyboardInterrupt:
            print("\n[RUN] Stopping...")
        finally:
            cap.release()
            if self.show_window and OPENCV_AVAILABLE:
                cv2.destroyAllWindows()
            print(f"[RUN] Done. Total frames: {self._frame_count}")


def main():
    parser = argparse.ArgumentParser(description="StreamDiffusion TouchDesigner Bridge")
    parser.add_argument("--config", default="configs/sdturbo_fast.yaml", help="Config YAML file")
    parser.add_argument("--webcam", type=int, default=0, help="Webcam device index")
    parser.add_argument("--no-window", action="store_true", help="Disable display window")
    args = parser.parse_args()

    cfg = load_config(args.config)
    bridge = StreamBridge(
        config=cfg,
        config_path=args.config,
        webcam_id=args.webcam,
        show_window=not args.no_window,
    )
    bridge.run()


if __name__ == "__main__":
    main()
