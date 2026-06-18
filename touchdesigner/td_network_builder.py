"""
td_network_builder.py — StreamDiffusion TouchDesigner Network Builder
=====================================================================
Run this INSIDE TouchDesigner to build the StreamDiffusion control interface.

NOTE: If you get a NameError on operator types (fileInTOP, oscInCHOP, etc.),
use the MANUAL SETUP instead — it takes 2 minutes and is more reliable:
  See: docs/touchdesigner-setup.md -> "Manual build" section

How to use (auto-build):
  1. Start td_bridge.py in a terminal (wait for [INIT] Model ready.)
  2. Open TouchDesigner -> new empty project
  3. Tab -> Text DAT -> paste this file -> right-click -> Run Script
  4. If it errors, switch to the manual steps in touchdesigner-setup.md

What gets built (if successful):
  - output_view  TOP : live diffused output image
  - input_view   TOP : live raw webcam input
  - osc_out      CHOP: sends /prompt /strength /seed /model /pause to Python (port 9000)
  - osc_in       CHOP: receives /fps /vram_used /status from Python (port 9001)
  - control      DAT : edit prompt/strength here, right-click Run Script to send
  - switch_*     DATs: model switching scripts

If the auto-build fails, create these 4 nodes manually:
  Tab -> TOP -> File In  (file = td_out/output_frame.png, Cook Rate = Every Frame, Always Active = On)
  Tab -> CHOP -> OSC Out (address = 127.0.0.1, port = 9000)
  Tab -> CHOP -> OSC In  (port = 9001, Active = On)
  Tab -> DAT -> Text     (paste the control script below)
"""

REPO_ROOT  = "D:/Github/StreamDiffusion"
OSC_IN_PORT  = 9001
OSC_OUT_PORT = 9000
OSC_HOST     = "127.0.0.1"

OUTPUT_PNG = f"{REPO_ROOT}/td_out/output_frame.png"
INPUT_PNG  = f"{REPO_ROOT}/td_out/input_frame.png"

# Control script — also paste this manually into a Text DAT if auto-build fails
CONTROL_SCRIPT = f"""\
osc = op('oscout1')   # default OSC Out name; change if yours is different

# --- EDIT THESE ---
prompt   = "vivid oil painting, golden hour, cinematic"
strength = 0.6    # 0.0 = subtle, 1.0 = full transform
seed     = 42
# ------------------

osc.sendOSC('/prompt',   [prompt])
osc.sendOSC('/strength', [strength])
osc.sendOSC('/seed',     [seed])
"""

MODEL_SCRIPTS = {
    'switch_sdturbo':  ("# SD-Turbo (~4.1 fps)\n"
                        "op('oscout1').sendOSC('/model', ['configs/sdturbo_fast.yaml'])"),
    'switch_kohaku':   ("# Kohaku (~3.4 fps)\n"
                        "op('oscout1').sendOSC('/model', ['configs/kohaku_quality.yaml'])"),
    'switch_art':      ("# Art install - 7 presets\n"
                        "op('oscout1').sendOSC('/model', ['configs/consciousness_projection.yaml'])"),
    'switch_tensorrt': ("# TensorRT (~5.6 fps)\n"
                        "op('oscout1').sendOSC('/model', ['configs/sdturbo_tensorrt.yaml'])"),
}

PRESET_SCRIPT = "op('oscout1').sendOSC('/prompt_index', [{i}])"


def _make_dat(parent_op, name, text, x=0, y=0):
    d = parent_op.create(textDAT, name)
    d.clear()
    d.write(text)
    d.nodeX, d.nodeY = x, y
    return d


def build():
    root = op('/')

    # Remove old network if rebuilding
    for child in root.findChildren(name='StreamDiffusion', maxDepth=1):
        try:
            child.destroy()
        except Exception:
            pass

    net = root.create(containerCOMP, 'StreamDiffusion')
    net.nodeX, net.nodeY = 0, 0

    # File In TOPs — use string-based parameter setting to avoid version issues
    try:
        out_top = net.create(fileInTOP, 'output_view')
    except NameError:
        print("[ERROR] fileInTOP not defined in this TD version.")
        print("        Use manual setup: Tab -> TOP -> File In")
        print(f"        File: {OUTPUT_PNG}")
        print("        Cook Rate: Every Frame, Always Active: On")
        print()
        print("        Then: Tab -> CHOP -> OSC Out (port 9000)")
        print("              Tab -> CHOP -> OSC In  (port 9001)")
        print()
        print("        Control DAT (Tab -> DAT -> Text, paste and right-click Run Script):")
        print()
        print(CONTROL_SCRIPT)
        return

    out_top.par.file = OUTPUT_PNG
    out_top.par.cookrate = 1
    out_top.par.alwayson = 1
    out_top.nodeX, out_top.nodeY = -400, 200

    inp_top = net.create(fileInTOP, 'input_view')
    inp_top.par.file = INPUT_PNG
    inp_top.par.cookrate = 1
    inp_top.par.alwayson = 1
    inp_top.nodeX, inp_top.nodeY = -700, 200

    # OSC
    osc_out = net.create(oscOutCHOP, 'osc_out')
    osc_out.par.address = OSC_HOST
    osc_out.par.port = OSC_OUT_PORT
    osc_out.nodeX, osc_out.nodeY = 200, 0

    osc_in = net.create(oscInCHOP, 'osc_in')
    osc_in.par.port = OSC_IN_PORT
    osc_in.par.active = 1
    osc_in.nodeX, osc_in.nodeY = 200, 200

    # Control DAT
    _make_dat(net, 'control', CONTROL_SCRIPT, -400, -100)

    # Model switch DATs
    x = -700
    for name, script in MODEL_SCRIPTS.items():
        _make_dat(net, name, script, x, -250)
        x += 200

    # Preset DATs
    for i in range(7):
        _make_dat(net, f'preset_{i}',
                  f"# Art preset {i}\n" + PRESET_SCRIPT.format(i=i),
                  -700 + i * 100, -350)

    print("[StreamDiffusion] Network built in /StreamDiffusion")
    print(f"  output_view TOP -> {OUTPUT_PNG}")
    print(f"  input_view  TOP -> {INPUT_PNG}")
    print(f"  osc_out CHOP    -> 127.0.0.1:{OSC_OUT_PORT}")
    print(f"  osc_in  CHOP    -> port {OSC_IN_PORT}")
    print()
    print("Next:")
    print("  1. Open output_view TOP -> right-click -> View")
    print("  2. Edit 'control' DAT prompt/strength -> right-click -> Run Script")
    print("  3. Right-click switch_sdturbo / switch_kohaku -> Run Script to swap models")


build()
