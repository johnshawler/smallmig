#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Boot the probe and recover actual native result bytes optically from its plane."""
import json, os, pathlib, signal, struct, subprocess, sys, time
from PIL import Image
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]
OUT=ROOT/'build/probe'; E=ROOT/'evidence/probe'; T=ROOT/'.tools/usr/bin'
negative='--negative' in sys.argv; tag='negative' if negative else 'positive'
meta=json.loads((OUT/'fixture-metadata.json').read_text()); count=meta['target_fixture_count']
E.mkdir(exist_ok=True,parents=True)
number=next(n for n in range(101,120) if not pathlib.Path(f'/tmp/.X11-unix/X{n}').exists())
env=dict(os.environ,DISPLAY=f':{number}',SDL_VIDEODRIVER='x11',SDL_VIDEO_X11_XRANDR='0',ALSOFT_DRIVERS='null',XDG_DATA_HOME=str(OUT/'xdg'),XDG_CACHE_HOME=str(OUT/'cache'))
xserver=subprocess.Popen([str(T/'Xvfb'),f':{number}','-screen','0','1024x768x24','-ac','-noreset','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
base=OUT/('fs-uae-'+tag); base.mkdir(exist_ok=True)
rom=ROOT/'build/kickstart.rom'
assert rom.exists(), 'Run the original harness once to resolve its supplied ROM.'
config=f'''[fs-uae]
base_dir = {base}
amiga_model = A1200
cpu = 68EC020
chip_memory = 2048
fast_memory = 8192
kickstart_file = {rom}
floppy_drive_0 = {OUT/('negative.adf' if negative else 'probe.adf')}
writable_floppy_images = 0
floppy_drive_0_sounds = 0
fullscreen = 0
window_width = 960
window_height = 720
video_sync = off
'''
(OUT/(tag+'.fs-uae')).write_text(config)
def white(c): return min(c)>200

def decode(path):
    im=Image.open(path).convert('RGB')
    # Calibration rows span all 320 pixels; data rows rarely have >95% white.
    runs=[]; band=[]
    for y in range(im.height):
        xs=[x for x in range(im.width) if white(im.getpixel((x,y)))]
        if len(xs)>750:
            band.append(y)
        elif band:
            runs.append((band[0],band[-1])); band=[]
    if len(runs)<8: return None
    runs=runs[:8]; centers=[(a+b)/2 for a,b in runs]
    # White calibration logical lines are 0,2,...14. Fit scale and intercept.
    ns=list(range(0,16,2)); nm=sum(ns)/8; ym=sum(centers)/8
    sy=sum((n-nm)*(y-ym) for n,y in zip(ns,centers))/sum((n-nm)**2 for n in ns)
    y0=ym-sy*nm
    y=int(round(centers[0])); xs=[x for x in range(im.width) if white(im.getpixel((x,y)))]
    x0=min(xs); sx=(max(xs)-x0+1)/320
    data=bytearray()
    for byte_index in range(count*10+32):
        logical_row=16+byte_index//40; col=(byte_index%40)*8
        val=0
        for bit in range(8):
            x=int(x0+(col+bit+.5)*sx)
            y=int(round(y0+logical_row*sy))
            val=(val<<1)|white(im.getpixel((x,y)))
        data.append(val)
    background=im.getpixel((20,20))
    # Background sample immediately below the calibration band, outside data.
    bg=im.getpixel((int(x0+10*sx),int(round(y0+100*sy))))
    return bytes(data), {'origin_x':x0,'row0_center_y':y0,'scale_x':sx,'scale_y':sy,'background_rgb':list(bg)}
proc=None
try:
    for _ in range(50):
        if subprocess.run(['xdpyinfo'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
        time.sleep(.1)
    time.sleep(1)
    with open(E/(tag+'-stdout.txt'),'w') as log:
        proc=subprocess.Popen([str(T/'fs-uae'),str(OUT/(tag+'.fs-uae'))],env=env,stdout=log,stderr=log,start_new_session=True)
        deadline=time.monotonic()+55
        while time.monotonic()<deadline:
            if proc.poll() is not None: raise RuntimeError('Emulator exited before results')
            path=E/(tag+'.png')
            subprocess.run(['import','-window','root',str(path)],env=env,check=True,timeout=5)
            decoded=decode(path)
            if decoded and decoded[0][count*10:count*10+4]==b'PROB': break
            time.sleep(.7)
        else: raise RuntimeError('No decoded PROB completion marker in 55 seconds')
finally:
    if proc and proc.poll() is None:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    xserver.terminate();xserver.wait(timeout=5)
data,cal=decoded
actual=data[:count*10]; expected=(OUT/'expected-output.bin').read_bytes()
(E/(tag+'-actual-output.bin')).write_bytes(actual)
assert actual==expected, next((i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
magic,ticks,iterations,allocation,chip_before,fast_before,chip_after,fast_after=struct.unpack('>4sIIIIIII',data[count*10:])
assert magic==b'PROB' and iterations==20000 and allocation==32768
assert chip_before-chip_after==32768 and fast_before==fast_after, (chip_before,chip_after,fast_before,fast_after)
bg=cal['background_rgb']; target_failed=bg[0]>bg[1]
assert target_failed==negative,(target_failed,negative,cal)
report={'target':'FS-UAE A1200 / 68EC020 / AGA / 2 MiB Chip / 8 MiB Fast',
        'negative_control_expected_mismatch':negative,'target_self_check_failed':target_failed,
        'actual_bytes_match_uncorrupted_reference':True,'compared_cases':count,'compared_bytes':len(actual),
        'output_fields':meta['output_fields'],'cia_elapsed_ticks':ticks,'benchmark_iterations':iterations,
        'assumed_pal_e_clock_hz':709379,'emulated_seconds':ticks/709379,
        'emulated_microseconds_per_update_including_call_and_loop':ticks/709379/iterations*1e6,
        'explicit_chip_allocation_bytes':allocation,'explicit_fast_allocation_bytes':0,
        'allocator_free_chip_before':chip_before,'allocator_free_chip_after':chip_after,
        'allocator_free_fast_before':fast_before,'allocator_free_fast_after':fast_after,
        'measured_chip_free_delta_bytes':chip_before-chip_after,'measured_fast_free_delta_bytes':fast_before-fast_after,
        'memory_high_water_measured':False,'timing_hardware_validated':False,'optical_calibration':cal}
(E/(tag+'-report.json')).write_text(json.dumps(report,indent=2)+'\n')
logpath=base/'Cache/Logs/fs-uae.log.txt'
if logpath.exists(): (E/(tag+'-emulator.log')).write_bytes(logpath.read_bytes())
print(json.dumps(report,indent=2))
