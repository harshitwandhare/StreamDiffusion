"""
StreamDiffusion TD Component Builder
=====================================
Paste this entire script into a Text DAT in TouchDesigner 2023,
then right-click the DAT → Run Script.

It will auto-build a "StreamDiffusionTD" Container COMP in your network
with a full UI, NDI input, OSC control, subprocess management, and callbacks.

After building: right-click the component → Save Component As → StreamDiffusionTD.tox
to save it for reuse in future projects.

Requires: td_ndi_bridge.py and the StreamDiffusion venv at the base folder path.
"""

import os
import re

# ── helpers ───────────────────────────────────────────────────────────────────

def _clean(ops):
    for o in ops:
        try:
            o.destroy()
        except Exception:
            pass


def _place(o, x, y):
    o.nodeX = x
    o.nodeY = y


def _connect(src, dst, out_idx=0, in_idx=0):
    dst.inputConnectors[in_idx].connect(src.outputConnectors[out_idx])


# ── main builder ──────────────────────────────────────────────────────────────

def build():
    root = op('/')

    # Remove old build if re-running
    old = op('/StreamDiffusionTD')
    if old:
        old.destroy()

    comp = root.create(containerCOMP, 'StreamDiffusionTD')
    comp.nodeX = 0
    comp.nodeY = 0
    comp.comment = 'StreamDiffusion real-time diffusion bridge'

    # ── Custom parameter pages ─────────────────────────────────────────────────

    # --- Setup page ---
    setup = comp.appendCustomPage('Setup')

    p = setup.appendFile('Basefolder', label='Base Folder')
    p[0].default = r'D:\Github\StreamDiffusion'
    p[0].help = 'Path to your StreamDiffusion installation (contains .venv folder)'

    p = setup.appendMenu('Config', label='Config')
    p[0].menuNames  = ['sdturbo_fast', 'sdturbo_tensorrt', 'kohaku_quality', 'consciousness_projection']
    p[0].menuLabels = ['SD-Turbo xformers (~4.7 fps)', 'SD-Turbo TensorRT (~5.8 fps)', 'Kohaku quality (~3.4 fps)', 'Art installation preset']
    p[0].default = 0

    p = setup.appendInt('Webcam', label='Webcam Index')
    p[0].default = 0
    p[0].min = 0
    p[0].max = 8

    p = setup.appendMenu('Transport', label='Video Transport')
    p[0].menuNames  = ['ndi', 'png']
    p[0].menuLabels = ['NDI (recommended)', 'PNG fallback']
    p[0].default = 0

    p = setup.appendInt('Oscin', label='OSC In Port (Python listens)')
    p[0].default = 9000

    p = setup.appendInt('Oscout', label='OSC Out Port (stats to TD)')
    p[0].default = 9001

    p = setup.appendPulse('Startstream', label='▶  Start Stream')
    p = setup.appendPulse('Stopstream',  label='■  Stop Stream')

    # --- Settings page ---
    settings = comp.appendCustomPage('Settings')

    p = settings.appendStr('Prompt', label='Prompt')
    p[0].default = 'vivid impressionist painting, dynamic light'

    p = settings.appendStr('Negative', label='Negative Prompt')
    p[0].default = 'blurry, low quality, watermark'

    p = settings.appendFloat('Strength', label='Strength')
    p[0].default = 0.75
    p[0].min = 0.3
    p[0].max = 0.99
    p[0].clampMin = True
    p[0].clampMax = True

    p = settings.appendFloat('Guidancescale', label='Guidance Scale')
    p[0].default = 1.2
    p[0].min = 1.0
    p[0].max = 2.0

    p = settings.appendInt('Seed', label='Seed (-1 = random)')
    p[0].default = 42
    p[0].min = -1

    p = settings.appendToggle('Similarfilter', label='Similar Image Filter')
    p[0].default = True

    # --- Info page ---
    info = comp.appendCustomPage('Info')

    p = info.appendStr('Streamfps',  label='Stream FPS')
    p[0].readOnly = True
    p[0].default = '--'

    p = info.appendStr('Vramused', label='VRAM Used (GB)')
    p[0].readOnly = True
    p[0].default = '--'

    p = info.appendStr('Status', label='Status')
    p[0].readOnly = True
    p[0].default = 'stopped'

    p = info.appendStr('Bridgescript', label='Bridge Script')
    p[0].readOnly = True
    p[0].default = 'td_ndi_bridge.py'

    # ── Internal operators ─────────────────────────────────────────────────────

    # NDI In TOP — receives video from Python bridge
    ndi_in = comp.create(ndiinTOP, 'ndi_in')
    ndi_in.par.sourcename = 'StreamDiffusion'
    ndi_in.par.bandwidth = 'Highest'
    ndi_in.par.cookrate = -1
    _place(ndi_in, -400, 200)

    # Null TOP — output
    null_out = comp.create(nullTOP, 'OUT')
    _place(null_out, 200, 200)
    _connect(ndi_in, null_out)

    # OSC In CHOP — receives stats from Python (/fps /vram_used /status)
    osc_in = comp.create(oscchopCHOP, 'osc_in')
    osc_in.par.networkport = me.parent().par.Oscout.eval()  # TD receives on the "out" port
    osc_in.par.port = 9001
    _place(osc_in, -400, -100)

    # OSC Out CHOP — sends control to Python
    osc_out = comp.create(oscoutCHOP, 'osc_out')
    osc_out.par.networkaddress = '127.0.0.1'
    osc_out.par.networkport = 9000
    _place(osc_out, -400, -300)

    # Script DAT — subprocess manager + OSC stats reader
    script_dat = comp.create(scriptDAT, 'controller')
    _place(script_dat, 200, -200)
    script_dat.text = _controller_script()

    # Execute DAT — fires on parameter changes to send OSC
    exec_dat = comp.create(executeDAT, 'param_executor')
    exec_dat.par.active = True
    exec_dat.par.valuechange = True
    _place(exec_dat, 400, -200)
    exec_dat.text = _executor_script()

    # Text DAT — instructions
    help_dat = comp.create(textDAT, 'README')
    _place(help_dat, 600, 200)
    help_dat.text = _readme_text()

    print('✓ StreamDiffusionTD built at /StreamDiffusionTD')
    print('  → Setup page: set Base Folder, pick Config, hit Start Stream')
    print('  → To save as .tox: right-click → Save Component As...')


# ── embedded scripts ──────────────────────────────────────────────────────────

def _controller_script():
    return '''\
# StreamDiffusion controller — runs as Script DAT
# Call run('start') or run('stop') from parameter callbacks

import subprocess
import sys
import os
import threading

_proc = None

def start():
    global _proc
    if _proc and _proc.poll() is None:
        print('[SD] already running')
        return

    comp = op('/StreamDiffusionTD')
    base  = comp.par.Basefolder.eval()
    cfg_names = ['sdturbo_fast', 'sdturbo_tensorrt', 'kohaku_quality', 'consciousness_projection']
    cfg   = cfg_names[int(comp.par.Config.eval())]
    cam   = int(comp.par.Webcam.eval())
    transport = comp.par.Transport.eval()

    script = 'td_ndi_bridge.py' if transport == 'ndi' else 'td_bridge.py'
    python = os.path.join(base, '.venv', 'Scripts', 'python.exe')
    script_path = os.path.join(base, 'touchdesigner', script)
    config_path = os.path.join(base, 'configs', cfg + '.yaml')

    if not os.path.exists(python):
        print(f'[SD] venv not found at {python}')
        comp.par.Status = 'error: venv missing'
        return

    cmd = [python, script_path, '--config', config_path, '--webcam', str(cam),
           '--osc_in', '9000', '--osc_out', '9001']

    print(f'[SD] starting: {" ".join(cmd)}')
    comp.par.Status = 'starting...'

    _proc = subprocess.Popen(
        cmd,
        cwd=base,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # stream output to textport
    def _read():
        for line in _proc.stdout:
            print('[SD]', line.rstrip())
            if '[ready]' in line or 'StreamDiffusion active' in line:
                comp.par.Status = 'running'
        comp.par.Status = 'stopped'
    threading.Thread(target=_read, daemon=True).start()


def stop():
    global _proc
    comp = op('/StreamDiffusionTD')
    if _proc:
        _proc.terminate()
        _proc = None
    comp.par.Status = 'stopped'
    print('[SD] stopped')


def run(cmd):
    if cmd == 'start':
        start()
    elif cmd == 'stop':
        stop()
'''


def _executor_script():
    return '''\
# Fires when component parameters change — sends OSC to Python bridge
import json

def onValueChange(par, prev):
    comp = op('/StreamDiffusionTD')
    osc  = comp.op('osc_out')

    if par.name == 'Prompt':
        osc.sendOSC('/prompt', [par.eval()])

    elif par.name == 'Negative':
        osc.sendOSC('/negative', [par.eval()])

    elif par.name == 'Strength':
        osc.sendOSC('/strength', [float(par.eval())])

    elif par.name == 'Seed':
        osc.sendOSC('/seed', [int(par.eval())])

    elif par.name == 'Startstream':
        comp.op('controller').run("run(\'start\')")

    elif par.name == 'Stopstream':
        comp.op('controller').run("run(\'stop\')")


def onPulse(par):
    onValueChange(par, None)
'''


def _readme_text():
    return """\
StreamDiffusionTD — Quick Start
================================

1. Setup page:
   - Base Folder → path to your StreamDiffusion install
     (the folder containing .venv, td_ndi_bridge.py, configs/)
   - Config → pick a preset
   - Webcam → index of your camera (0 = first)

2. Hit [Start Stream]
   A command window launches the Python bridge.
   Wait for status = "running" on the Info page.

3. In your TD network:
   - Connect OUT (the NDI In TOP) to your chain
   - Drag this component's Prompt / Strength / Seed params
     to sliders, text boxes, or CHOP values

4. OSC control (from other apps / CHOP):
   Send to 127.0.0.1:9000
     /prompt   string
     /strength float  (0.3 – 0.99)
     /seed     int
     /pause    int    (0 or 1)

   Receive from 127.0.0.1:9001
     /fps       float
     /vram_used float
     /status    string

5. Hit [Stop Stream] to shut down the bridge.

Notes:
- TensorRT config compiles GPU kernels on first run (~53s, looks frozen — wait)
- Negative prompts have limited effect with SD-Turbo (known limitation)
- Keep Guidance Scale between 1.0–1.5
"""


# ── run ───────────────────────────────────────────────────────────────────────

build()
