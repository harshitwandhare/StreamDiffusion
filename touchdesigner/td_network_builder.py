"""
td_network_builder.py — StreamDiffusion TouchDesigner Network Builder
=====================================================================
Run this INSIDE TouchDesigner to build the full StreamDiffusion control interface.

How to use:
  1. Start td_bridge.py in a terminal first (wait for [INIT] Model ready.)
  2. Open TouchDesigner -> new empty project
  3. Tab -> Text DAT -> paste this entire file -> right-click -> Run Script
  4. The full UI network is created automatically

What gets built:
  - input_view   : live webcam input (raw, before diffusion)
  - output_view  : live diffused output
  - osc_in       : receives /fps /vram_used /status /model_name /prompt_current from Python
  - osc_out      : sends /prompt /strength /seed /model /pause to Python
  - prompt_box   : editable text field for live prompt changes
  - strength_val : float slider 0.0-1.0 (transformation strength)
  - seed_val     : integer field for seed
  - stats_text   : live FPS/VRAM/status readout
  - controller   : CHOP Execute DAT — wires all controls to OSC out
  - model_sd     : button — switch to SD-Turbo (fast, ~4.8 fps)
  - model_kohaku : button — switch to Kohaku (quality, ~3.4 fps)
  - model_art    : button — switch to consciousness_projection (art, 7 presets)
  - model_trt    : button — switch to TensorRT (fastest, ~5.8 fps)
  - preset_0..6  : buttons for cycling art installation prompts
"""

import re

# ---- Config ---------------------------------------------------------------
REPO_ROOT = "D:/Github/StreamDiffusion"   # forward slashes required in TD
OSC_IN_PORT  = 9001
OSC_OUT_PORT = 9000
OSC_HOST     = "127.0.0.1"

CONFIGS = {
    "sd_turbo":   "configs/sdturbo_fast.yaml",
    "kohaku":     "configs/kohaku_quality.yaml",
    "art":        "configs/consciousness_projection.yaml",
    "tensorrt":   "configs/sdturbo_tensorrt.yaml",
}

INPUT_PNG  = f"{REPO_ROOT}/td_out/input_frame.png"
OUTPUT_PNG = f"{REPO_ROOT}/td_out/output_frame.png"

# ---- Helpers --------------------------------------------------------------

def place(op_obj, x, y):
    op_obj.nodeX = x
    op_obj.nodeY = y
    return op_obj


def make_text_dat(parent_op, name, text, x=0, y=0):
    d = parent_op.create(textDAT, name)
    d.clear()
    d.write(text)
    place(d, x, y)
    return d


# ---- Build network --------------------------------------------------------

def build():
    root = op('/')

    # Remove old network if rebuilding
    for name in ['StreamDiffusion']:
        old = root.findChildren(name=name, maxDepth=1)
        for o in old:
            try:
                o.destroy()
            except Exception:
                pass

    # Top-level container
    net = root.create(containerCOMP, 'StreamDiffusion')
    place(net, 0, 0)
    net.par.w = 1280
    net.par.h = 720

    p = net  # shorthand: parent for all nodes below

    # ------------------------------------------------------------------
    # 1. File In TOPs — input (raw) and output (diffused)
    # ------------------------------------------------------------------
    inp = p.create(fileInTOP, 'input_view')
    inp.par.file = INPUT_PNG
    inp.par.reloadpulse.pulse()
    # Cook every frame so TD polls the PNG continuously
    inp.par.cookrate = 1        # "Every Frame"
    inp.par.alwayson = 1
    place(inp, -600, 200)

    out = p.create(fileInTOP, 'output_view')
    out.par.file = OUTPUT_PNG
    out.par.cookrate = 1
    out.par.alwayson = 1
    place(out, -200, 200)

    # ------------------------------------------------------------------
    # 2. OSC nodes
    # ------------------------------------------------------------------
    osc_in = p.create(oscInCHOP, 'osc_in')
    osc_in.par.port = OSC_IN_PORT
    osc_in.par.active = 1
    place(osc_in, 400, 200)

    osc_out = p.create(oscOutCHOP, 'osc_out')
    osc_out.par.address = OSC_HOST
    osc_out.par.port = OSC_OUT_PORT
    place(osc_out, 400, 0)

    # ------------------------------------------------------------------
    # 3. Controls — prompt text, strength slider, seed
    # ------------------------------------------------------------------
    prompt_dat = make_text_dat(p, 'prompt_text',
        "vivid digital painting, dynamic lighting, cinematic", -600, -100)
    prompt_dat.par.rows = 3

    strength_dat = make_text_dat(p, 'strength_text', "0.5", -200, -100)

    seed_dat = make_text_dat(p, 'seed_text', "42", 0, -100)

    # ------------------------------------------------------------------
    # 4. Stats display DAT (reads from OSC In CHOP)
    # ------------------------------------------------------------------
    stats_script = """\
# Auto-updates every cook to show live stats from Python backend
# This DAT is set to 'Always Cook'
osc = op('osc_in')
fps   = osc['fps'][0]   if osc['fps']   else 0.0
vram  = osc['vram_used'][0] if osc['vram_used'] else 0.0
status = osc['status'][0] if osc['status'] else '?'
model  = osc['model_name'][0] if osc['model_name'] else '?'
prompt = osc['prompt_current'][0] if osc['prompt_current'] else '?'

me.clear()
me.appendRow(['FPS',    f'{fps:.1f}'])
me.appendRow(['VRAM',   f'{vram:.0f} MB'])
me.appendRow(['Status', str(status)])
me.appendRow(['Model',  str(model)])
me.appendRow(['Prompt', str(prompt)[:60]])
"""
    stats = p.create(scriptDAT, 'stats_text')
    stats.clear()
    stats.write(stats_script)
    stats.par.alwayson = 1
    stats.par.cookrate = 1
    place(stats, 600, 200)

    # ------------------------------------------------------------------
    # 5. Controller CHOP Execute DAT
    #    Watches prompt_text / strength_text / seed_text DATs
    #    and sends OSC whenever they change
    # ------------------------------------------------------------------
    controller_script = """\
# CHOP Execute — fires when any watched CHOP changes
# (attach this to a Null CHOP that references osc_in so it cooks)

def onOffToOn(channel, sampleIndex, val, prev):
    pass

def whileOn(channel, sampleIndex, val, prev):
    pass

def onOnToOff(channel, sampleIndex, val, prev):
    pass

def whileOff(channel, sampleIndex, val, prev):
    pass

def onValueChange(channel, sampleIndex, val, prev):
    pass
"""

    # A better approach: Script DAT that fires via a Timer CHOP every 100ms
    # and diffs against last sent values
    sender_script = """\
# Script DAT — run manually or via Execute DAT
# Call: op('sender').run()

osc = op('osc_out')

def send_prompt():
    txt = op('prompt_text')[0, 0].val.strip()
    if txt:
        osc.sendOSC('/prompt', [txt])

def send_strength():
    try:
        val = float(op('strength_text')[0, 0].val)
        val = max(0.0, min(1.0, val))
        osc.sendOSC('/strength', [val])
    except Exception:
        pass

def send_seed():
    try:
        val = int(op('seed_text')[0, 0].val)
        osc.sendOSC('/seed', [val])
    except Exception:
        pass

def switch_model(config_key):
    configs = {
        'sd_turbo':  'configs/sdturbo_fast.yaml',
        'kohaku':    'configs/kohaku_quality.yaml',
        'art':       'configs/consciousness_projection.yaml',
        'tensorrt':  'configs/sdturbo_tensorrt.yaml',
    }
    path = configs.get(config_key, '')
    if path:
        osc.sendOSC('/model', [path])

def send_preset(index):
    osc.sendOSC('/prompt_index', [int(index)])

def pause():
    osc.sendOSC('/pause', [1])

def resume():
    osc.sendOSC('/pause', [0])
"""
    sender = make_text_dat(p, 'sender', sender_script, 200, -100)

    # ------------------------------------------------------------------
    # 6. Execute DAT — auto-fires sender functions
    #    Watches the prompt/strength/seed text DATs via callbacks
    # ------------------------------------------------------------------
    exec_script = """\
# DAT Execute — fires when watched DATs change
# Attach: Edit > Parameters > Dat Execute > DATs = prompt_text strength_text seed_text

def onTableChange(dat):
    s = op('sender')
    if dat.name == 'prompt_text':
        s.run(endFrame=True, delayFrames=2)   # small delay so typing settles
        # Direct call:
        osc = op('osc_out')
        txt = dat[0, 0].val.strip()
        if txt:
            osc.sendOSC('/prompt', [txt])
    elif dat.name == 'strength_text':
        try:
            val = float(dat[0, 0].val)
            op('osc_out').sendOSC('/strength', [max(0.0, min(1.0, val))])
        except Exception:
            pass
    elif dat.name == 'seed_text':
        try:
            op('osc_out').sendOSC('/seed', [int(dat[0, 0].val)])
        except Exception:
            pass
"""
    executor = p.create(datExecuteDAT, 'executor')
    executor.clear()
    executor.write(exec_script)
    # Watch prompt + strength + seed DATs
    executor.par.dats = 'prompt_text strength_text seed_text'
    place(executor, 200, -200)

    # ------------------------------------------------------------------
    # 7. Model-switch button scripts (Text DATs — right-click Run Script)
    # ------------------------------------------------------------------
    model_buttons = [
        ('switch_sdturbo',   "op('osc_out').sendOSC('/model', ['configs/sdturbo_fast.yaml'])",
         "SD-Turbo (~4.8fps)", -600, -300),
        ('switch_kohaku',    "op('osc_out').sendOSC('/model', ['configs/kohaku_quality.yaml'])",
         "Kohaku (~3.4fps)", -400, -300),
        ('switch_art',       "op('osc_out').sendOSC('/model', ['configs/consciousness_projection.yaml'])",
         "Art Install", -200, -300),
        ('switch_tensorrt',  "op('osc_out').sendOSC('/model', ['configs/sdturbo_tensorrt.yaml'])",
         "TensorRT (~5.8fps)", 0, -300),
    ]
    for name, code, label, x, y in model_buttons:
        d = make_text_dat(p, name, f"# {label}\n{code}", x, y)

    # Preset index buttons for art config
    for i in range(7):
        d = make_text_dat(p, f'preset_{i}',
            f"# Art preset {i}\nop('osc_out').sendOSC('/prompt_index', [{i}])",
            -600 + i * 100, -400)

    # Pause / resume
    make_text_dat(p, 'pause_btn',  "op('osc_out').sendOSC('/pause', [1])", 200, -300)
    make_text_dat(p, 'resume_btn', "op('osc_out').sendOSC('/pause', [0])", 300, -300)

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    print("\n[StreamDiffusion] Network built successfully.")
    print(f"  Container: /StreamDiffusion")
    print(f"  input_view  -> {INPUT_PNG}")
    print(f"  output_view -> {OUTPUT_PNG}")
    print(f"  OSC in  port {OSC_IN_PORT}  (receives /fps /vram /status from Python)")
    print(f"  OSC out port {OSC_OUT_PORT}  (sends /prompt /strength /seed /model to Python)")
    print()
    print("Next steps:")
    print("  1. Set input_view and output_view File par -> Cook Rate = Every Frame, Always Active = On")
    print("  2. Edit prompt_text DAT to type your prompt -> executor DAT auto-sends it via OSC")
    print("  3. Right-click switch_sdturbo / switch_kohaku / switch_art -> Run Script to swap models")
    print("  4. Right-click preset_0..preset_6 -> Run Script to cycle art presets")


build()
