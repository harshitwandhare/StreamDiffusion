"""
download_model.py — Reliable sequential model downloader with retry
Falls back to sequential single-file downloads when HuggingFace
parallel snapshot_download fails mid-transfer.

IPv4 patch: forces all DNS resolution to return IPv4 addresses.
Required on networks where IPv6 connections to HuggingFace are reset
(common with some ISPs and corporate firewalls that filter IPv6 routes).
"""
import sys
import time
import socket as _socket

# Force IPv4 — prevents TLS handshake failures on networks that
# reset IPv6 connections to HuggingFace CDN endpoints.
_orig_getaddrinfo = _socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, _socket.AF_INET, type, proto, flags)
_socket.getaddrinfo = _ipv4_only

from huggingface_hub import hf_hub_download, list_repo_files

MODEL_ID = sys.argv[1] if len(sys.argv) > 1 else "KBlueLeaf/kohaku-v2.1"
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds between retries

def download_with_retry(repo_id, filename, max_retries=MAX_RETRIES):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  [{attempt}/{max_retries}] {filename}", end=" ... ", flush=True)
            path = hf_hub_download(repo_id=repo_id, filename=filename, resume_download=True)
            print("OK", flush=True)
            return path
        except Exception as e:
            if attempt < max_retries:
                print(f"RETRY ({e.__class__.__name__})", flush=True)
                time.sleep(RETRY_DELAY)
            else:
                print(f"FAILED: {e}", flush=True)
                return None

print(f"Downloading {MODEL_ID} (sequential, with retry)")
print("This avoids connection-reset issues from parallel downloads.\n")

try:
    files = list(list_repo_files(MODEL_ID))
    print(f"Found {len(files)} files to download.\n")
except Exception as e:
    print(f"Could not list repo files: {e}")
    sys.exit(1)

# Sort: small config files first, large weights last
files.sort(key=lambda f: (not f.endswith((".json", ".txt", ".yaml")), f))

ok, failed = 0, []
for fname in files:
    result = download_with_retry(MODEL_ID, fname)
    if result:
        ok += 1
    else:
        failed.append(fname)

print(f"\nDone: {ok}/{len(files)} files downloaded.")
if failed:
    print(f"Failed: {failed}")
    sys.exit(1)
else:
    print("All files ready. Model is cached at ~/.cache/huggingface/hub/")
