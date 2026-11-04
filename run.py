#!/usr/bin/env python3
"""Launch FS-UAE; a private ROM path is required, never shipped."""
import os, pathlib, subprocess, sys, time
root = pathlib.Path(__file__).resolve().parent
os.chdir(root)
build = root/'build'
if not (build/'harness.adf').exists():
    sys.exit('Build first: python3 build.py')
rom = os.environ.get('AMIGA_KICKSTART')
if not rom:
    sys.exit('Set AMIGA_KICKSTART to your private A1200 Kickstart 3.1 ROM path.')
base = build/'fs-uae'
base.mkdir(exist_ok=True)
config = f'''[fs-uae]
base_dir = {base}
amiga_model = A1200
cpu = 68EC020
chip_memory = 2048
fast_memory = 8192
kickstart_file = {pathlib.Path(rom).resolve()}
floppy_drive_0 = {build/'harness.adf'}
floppy_drive_0_sounds = 0
writable_floppy_images = 0
joystick_port_1 = keyboard
fullscreen = 0
window_width = 960
window_height = 720
video_sync = off
'''
(build/'harness.fs-uae').write_text(config)
exe = root/'.tools/usr/bin/fs-uae'
runtime = build/'runtime'
runtime.mkdir(exist_ok=True, mode=0o700)
env = dict(os.environ, FS_UAE_BASE_DIR=str(base), XDG_DATA_HOME=str(build/'xdg'), XDG_CACHE_HOME=str(build/'cache'), XDG_RUNTIME_DIR=str(runtime))
env.setdefault('SDL_VIDEODRIVER', 'x11')
env.setdefault('SDL_VIDEO_X11_XRANDR', '0')
if env.get('DISPLAY'):
    os.execve(str(exe),[str(exe),str(build/'harness.fs-uae'),*sys.argv[1:]], env)
# A cloud run still has one command. Use a private virtual display when needed.
number = next(n for n in range(101, 120) if not pathlib.Path(f'/tmp/.X11-unix/X{n}').exists())
env['DISPLAY'] = f':{number}'
env.setdefault('ALSOFT_DRIVERS', 'null')
xserver = subprocess.Popen([str(root/'.tools/usr/bin/Xvfb'), env['DISPLAY'], '-screen', '0', '1024x768x24', '-ac', '-noreset', '-nolisten', 'tcp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
proc = None
try:
    for _ in range(50):
        if pathlib.Path(f'/tmp/.X11-unix/X{number}').exists(): break
        if xserver.poll() is not None: sys.exit('Xvfb failed to start; see README.md.')
        time.sleep(.1)
    time.sleep(1)
    print(f"Virtual display {env['DISPLAY']}; silent audio. Ctrl+C stops. tools/verify.py records input, graphics and sound.", flush=True)
    proc = subprocess.Popen([str(exe),str(build/'harness.fs-uae'),*sys.argv[1:]], env=env)
    proc.wait()
except KeyboardInterrupt:
    pass
finally:
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try: proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()
    xserver.terminate()
    xserver.wait(timeout=5)
