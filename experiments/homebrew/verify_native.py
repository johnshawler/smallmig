#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Boot the probe and recover actual native result bytes optically from its plane."""
import array, json, os, pathlib, signal, struct, subprocess, sys, time
from PIL import Image
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]
OUT=ROOT/'build/homebrew'; E=ROOT/'evidence/homebrew'; T=ROOT/'.tools/usr/bin'
negative='--negative' in sys.argv; tag='negative' if negative else 'positive'
meta=json.loads((OUT/'fixture-metadata.json').read_text()); count=meta['target_fixture_count']; case_bytes=15
E.mkdir(exist_ok=True,parents=True)
number=next(n for n in range(101,120) if not pathlib.Path(f'/tmp/.X11-unix/X{n}').exists())
env=dict(os.environ,DISPLAY=f':{number}',SDL_VIDEODRIVER='x11',SDL_VIDEO_X11_XRANDR='0',ALSOFT_DRIVERS='wave',XDG_DATA_HOME=str(OUT/'xdg'),XDG_CACHE_HOME=str(OUT/'cache'))
audio_conf=OUT/'openal-wave.conf'
audio_conf.write_text(f'[general]\ndrivers = wave\n[wave]\nfile = {E/"native-audio.wav"}\n')
env['ALSOFT_CONF']=str(audio_conf)
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
floppy_drive_0 = {OUT/'falling-slice.adf'}
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
    if len(runs)<16: return None
    runs=runs[:16]; centers=[(a+b)/2 for a,b in runs]
    # Two distant calibration bands improve decoding accuracy for long outputs.
    ns=list(range(0,16,2))+list(range(200,216,2)); nm=sum(ns)/16; ym=sum(centers)/16
    sy=sum((n-nm)*(y-ym) for n,y in zip(ns,centers))/sum((n-nm)**2 for n in ns)
    y0=ym-sy*nm
    y=int(round(centers[0])); xs=[x for x in range(im.width) if white(im.getpixel((x,y)))]
    x0=min(xs); sx=(max(xs)-x0+1)/320
    data=bytearray()
    for byte_index in range(count*case_bytes+32):
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
            if decoded and decoded[0][count*case_bytes:count*case_bytes+4]==b'PROB': break
            time.sleep(.7)
        else: raise RuntimeError('No decoded PROB completion marker in 55 seconds')
        raw,cal=decoded
        (E/'native-pre-demo.bin').write_bytes(raw)
        xenv=dict(env,LD_LIBRARY_PATH=str(ROOT/'.tools/usr/lib/x86_64-linux-gnu'))
        def xdo(*args):
            return subprocess.check_output([str(T/'xdotool'),*args],env=xenv,text=True).strip()
        windows=xdo('search','--name','FS-UAE').splitlines()
        xdo('windowfocus',windows[0])
        def hold(key,seconds):
            xdo('keydown',key);time.sleep(seconds);xdo('keyup',key);time.sleep(.2)
        hold('Control_R',.1)
        def capture_character(name):
            dest=E/name
            subprocess.run(['import','-window','root',str(dest)],env=env,check=True)
            im=Image.open(dest).convert('RGB')
            pts=[(x,y) for y in range(im.height) for x in range(im.width)
                 if (lambda c:c[0]>160 and c[0]>c[1]+20 and c[1]>c[2]+20)(im.getpixel((x,y)))]
            assert pts,'No ROM-derived character visible'
            return [min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)]
        start=capture_character('native-character.png')
        hold('Right',.6);right=capture_character('native-right.png')
        assert right[0]>start[0]+20,(start,right)
        hold('Left',.6);left=capture_character('native-left.png')
        assert left[0]<right[0]-20,(left,right)
        hold('Right',3);boundary=capture_character('native-boundary.png')
        (E/'native-input-report.json').write_text(json.dumps({'character_screen_bounds':{'start':start,'right':right,'left':left,'right_wall':boundary},'right_and_left_passed':True,'graphics_source':'CHR and OAM template decoded from Falling ROM; adapted palette and mirrored pose','sound':'native Paula feedback; see native-audio-report.json','original_nes_soundtrack_translated':False},indent=2)+'\n')
finally:
    if proc and proc.poll() is None:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    xserver.terminate();xserver.wait(timeout=5)
data,cal=decoded
actual=data[:count*case_bytes]; expected=(OUT/'expected-output.bin').read_bytes()
(E/(tag+'-actual-output.bin')).write_bytes(actual)
assert actual==expected, next((i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
magic,ticks,iterations,allocation,chip_before,fast_before,chip_after,fast_after=struct.unpack('>4sIIIIIII',data[count*case_bytes:])
assert magic==b'PROB' and iterations==20000 and allocation==98304
assert chip_before-chip_after==98304 and fast_before==fast_after, (chip_before,chip_after,fast_before,fast_after)
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

subprocess.run(['ffmpeg','-y','-v','error','-i',str(E/'native-audio.wav'),'-f','f32le','-ac','1',str(OUT/'native-audio.f32')],check=True)
a=array.array('f');a.frombytes((OUT/'native-audio.f32').read_bytes())
active=[i for i,v in enumerate(a) if abs(v)>.002]
assert active,'No native Paula feedback captured'
groups=[];first=prev=active[0]
for i in active[1:]:
    if i-prev>4800:groups.append((first,prev));first=i
    prev=i
groups.append((first,prev));first,last=max(groups,key=lambda x:x[1]-x[0])
assert (last-first)/48000>.4
seg=a[first+4800:min(last,first+52800)]
hz=sum(seg[i-1]<=0<seg[i] for i in range(1,len(seg)))*48000/len(seg)
assert 250<hz<310,hz
sound={'verified':True,'native_feedback_not_nes_apu':True,'peak':max(abs(v) for v in a),'longest_active_seconds':(last-first)/48000,'estimated_hz':hz,'sample_rate':48000,'physical_listening':False}
(E/'native-audio-report.json').write_text(json.dumps(sound,indent=2)+'\n')
subprocess.run(['ffmpeg','-y','-v','error','-ss',str(max(0,first/48000-.1)),'-i',str(E/'native-audio.wav'),'-t',str((last-first)/48000+.2),'-c:a','pcm_s16le',str(E/'native-feedback-tone.wav')],check=True)
print('AUDIO',json.dumps(sound))
