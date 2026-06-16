"""
download_models_direct.py — Smart targeted model downloader
============================================================
Downloads only the files needed for StreamDiffusion (diffusers format).
Uses fp16 weights where available to halve download size.
Saves to local directories under D:/Github/models/ so configs can
point to local paths — avoids the HuggingFace cache entirely.

IPv4 patch applied up top — required on networks where IPv6 connections
to HuggingFace CDN get reset at the TLS handshake level.

Usage:
  python download_models_direct.py          # both models
  python download_models_direct.py sd       # sd-turbo only
  python download_models_direct.py kohaku   # kohaku only
"""

import os
import sys
import socket as _socket
import time

# Force IPv4 — prevents SSL/TLS reset on networks that block IPv6
# routes to cdn-lfs.huggingface.co.
_orig_getaddrinfo = _socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, _socket.AF_INET, type, proto, flags)
_socket.getaddrinfo = _ipv4_only

import requests

HF_BASE = "https://huggingface.co"
OUT_DIR = os.path.join(os.path.dirname(__file__), "models")

# Files needed for diffusers StableDiffusionPipeline.from_pretrained()
# Format: (repo_id, remote_filename, local_filename)
# local_filename strips the .fp16 suffix so from_pretrained finds them.
SD_TURBO_FILES = [
    ("stabilityai/sd-turbo", "model_index.json",                                "model_index.json"),
    ("stabilityai/sd-turbo", "scheduler/scheduler_config.json",                 "scheduler/scheduler_config.json"),
    ("stabilityai/sd-turbo", "text_encoder/config.json",                        "text_encoder/config.json"),
    ("stabilityai/sd-turbo", "text_encoder/model.fp16.safetensors",             "text_encoder/model.safetensors"),
    ("stabilityai/sd-turbo", "tokenizer/merges.txt",                            "tokenizer/merges.txt"),
    ("stabilityai/sd-turbo", "tokenizer/special_tokens_map.json",               "tokenizer/special_tokens_map.json"),
    ("stabilityai/sd-turbo", "tokenizer/tokenizer_config.json",                 "tokenizer/tokenizer_config.json"),
    ("stabilityai/sd-turbo", "tokenizer/vocab.json",                            "tokenizer/vocab.json"),
    ("stabilityai/sd-turbo", "unet/config.json",                                "unet/config.json"),
    ("stabilityai/sd-turbo", "unet/diffusion_pytorch_model.fp16.safetensors",   "unet/diffusion_pytorch_model.safetensors"),
    ("stabilityai/sd-turbo", "vae/config.json",                                 "vae/config.json"),
    ("stabilityai/sd-turbo", "vae/diffusion_pytorch_model.fp16.safetensors",    "vae/diffusion_pytorch_model.safetensors"),
]

KOHAKU_FILES = [
    ("KBlueLeaf/kohaku-v2.1", "model_index.json",                               "model_index.json"),
    ("KBlueLeaf/kohaku-v2.1", "scheduler/scheduler_config.json",                "scheduler/scheduler_config.json"),
    ("KBlueLeaf/kohaku-v2.1", "text_encoder/config.json",                       "text_encoder/config.json"),
    ("KBlueLeaf/kohaku-v2.1", "text_encoder/model.safetensors",                 "text_encoder/model.safetensors"),
    ("KBlueLeaf/kohaku-v2.1", "tokenizer/merges.txt",                           "tokenizer/merges.txt"),
    ("KBlueLeaf/kohaku-v2.1", "tokenizer/special_tokens_map.json",              "tokenizer/special_tokens_map.json"),
    ("KBlueLeaf/kohaku-v2.1", "tokenizer/tokenizer_config.json",                "tokenizer/tokenizer_config.json"),
    ("KBlueLeaf/kohaku-v2.1", "tokenizer/vocab.json",                           "tokenizer/vocab.json"),
    ("KBlueLeaf/kohaku-v2.1", "unet/config.json",                               "unet/config.json"),
    ("KBlueLeaf/kohaku-v2.1", "unet/diffusion_pytorch_model.safetensors",       "unet/diffusion_pytorch_model.safetensors"),
    ("KBlueLeaf/kohaku-v2.1", "vae/config.json",                                "vae/config.json"),
    ("KBlueLeaf/kohaku-v2.1", "vae/diffusion_pytorch_model.safetensors",        "vae/diffusion_pytorch_model.safetensors"),
    ("KBlueLeaf/kohaku-v2.1", "feature_extractor/preprocessor_config.json",     "feature_extractor/preprocessor_config.json"),
    ("KBlueLeaf/kohaku-v2.1", "safety_checker/config.json",                     "safety_checker/config.json"),
]


def file_url(repo_id, remote_filename):
    return f"{HF_BASE}/{repo_id}/resolve/main/{remote_filename}"


def download_file(url, dest_path, max_retries=5, retry_delay=10):
    """Download a single file with resume support and retry."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    existing_bytes = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0

    for attempt in range(1, max_retries + 1):
        try:
            headers = {}
            if existing_bytes > 0:
                headers["Range"] = f"bytes={existing_bytes}-"

            resp = requests.get(url, headers=headers, stream=True, timeout=30, allow_redirects=True)

            if resp.status_code == 416:
                print("  already complete")
                return True

            if resp.status_code not in (200, 206):
                raise RuntimeError(f"HTTP {resp.status_code}")

            total = int(resp.headers.get("content-length", 0))
            if resp.status_code == 206:
                total += existing_bytes

            mode = "ab" if existing_bytes > 0 else "wb"
            downloaded = existing_bytes
            last_print = time.time()

            with open(dest_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                    now = time.time()
                    if now - last_print >= 5:
                        if total > 0:
                            pct = 100 * downloaded / total
                            mb = downloaded / 1024**2
                            print(f"  {pct:.0f}%  ({mb:.0f} MB)", flush=True)
                        last_print = now

            print("  done", flush=True)
            return True

        except Exception as e:
            if attempt < max_retries:
                print(f"  retry {attempt}/{max_retries}: {e.__class__.__name__}", flush=True)
                time.sleep(retry_delay)
                # Refresh byte count for resume
                existing_bytes = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
            else:
                print(f"  FAILED after {max_retries} attempts: {e}", flush=True)
                return False


def download_model(file_list, model_name, out_subdir):
    out = os.path.join(OUT_DIR, out_subdir)
    print(f"\n{'='*60}")
    print(f"  {model_name}")
    print(f"  -> {out}")
    print(f"{'='*60}\n")

    ok, fail = 0, []
    for repo_id, remote, local in file_list:
        dest = os.path.join(out, local)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print(f"  [skip] {local}  (exists)")
            ok += 1
            continue
        url = file_url(repo_id, remote)
        print(f"  {local}", flush=True)
        success = download_file(url, dest)
        if success:
            ok += 1
        else:
            fail.append(local)

    print(f"\n  Result: {ok}/{len(file_list)} files OK")
    if fail:
        print(f"  Failed: {fail}")
    return len(fail) == 0


if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    os.makedirs(OUT_DIR, exist_ok=True)

    success = True
    if target in ("all", "sd"):
        success &= download_model(SD_TURBO_FILES, "stabilityai/sd-turbo (fp16 weights)", "sd-turbo")
    if target in ("all", "kohaku"):
        success &= download_model(KOHAKU_FILES, "KBlueLeaf/kohaku-v2.1", "kohaku-v2.1")

    print("\n" + ("All models ready." if success else "Some downloads failed — re-run to resume."))
    sys.exit(0 if success else 1)
