#!/usr/bin/env python3
"""Optional cloud smoke check. Needs Pillow, ffmpeg, import, and host X libraries."""
import array, json, os, pathlib, signal, subprocess, time
from PIL import Image
r = pathlib.Path(__file__).resolve().parents[1]
os.chdir(r)
e = r/'evidence'
e.mkdir(exist_ok=True)
t = r/'.tools/usr/bin'
env = dict(os.environ, SDL_VIDEODRIVER='x11', SDL_VIDEO_X11_XRANDR='0', LD_LIBRARY_PATH=str(r/'.tools/usr/lib/x86_64-linux-gnu'))
xserver = None
for n in range(101, 120):
    if not pathlib.Path(f'/tmp/.X11-unix/X{n}').exists():
        env['DISPLAY'] = f':{n}'
        xserver = subprocess.Popen([str(t/'Xvfb'),f':{n}','-screen','0','1024x768x24','-ac','-noreset','-nolisten','tcp'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        break
assert xserver is not None
conf = r/'build/openal-verify.conf'
conf.write_text(f'[general]\ndrivers = wave\n[wave]\nfile = {e/"audio.wav"}\n')
env['ALSOFT_CONF'] = str(conf)
def xdo(*args):
    return subprocess.check_output([str(t/'xdotool'),*args],env=env,text=True).strip()
def capture(name):
    dest = e/name
    subprocess.run(['import','-window','root',str(dest)],env=env,check=True)
    im=Image.open(dest).convert('RGB')
    pts=[(x,y) for y in range(im.height) for x in range(im.width) if (lambda c:c[0]<40 and c[1]>180 and c[2]>120)(im.getpixel((x,y)))]
    if not pts: return None
    return [min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)]
proc=None
try:
    for _ in range(50):
        if subprocess.run(['xdpyinfo'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0: break
        time.sleep(.1)
    log=open(e/'emulator-stdout.txt','w')
    time.sleep(1)
    proc=subprocess.Popen(['python3','run.py'],env=env,stdout=log,stderr=log,start_new_session=True)
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        windows=xdo('search','--name','FS-UAE') if subprocess.run([str(t/'xdotool'),'search','--name','FS-UAE'],env=env,stdout=subprocess.DEVNULL).returncode==0 else ''
        if windows:
            start=capture('boot.png')
            if start: break
        time.sleep(.5)
    else: raise RuntimeError('No visible sprite within 45 seconds')
    xdo('windowfocus',windows.splitlines()[0])
    def hold(key, seconds):
        xdo('keydown',key)
        time.sleep(seconds)
        xdo('keyup',key)
        time.sleep(.15)
    positions={'start': start}
    hold('Right',.65)
    positions['right']=capture('moved.png')
    assert positions['right'][0]>start[0], positions
    hold('Down',.4)
    positions['down']=capture('down.png')
    assert positions['down'][1]>positions['right'][1], positions
    hold('Left',.4)
    positions['left']=capture('left.png')
    assert positions['left'][0]<positions['down'][0], positions
    hold('Up',.4)
    positions['up']=capture('up.png')
    assert positions['up'][1]<positions['left'][1], positions
    hold('Control_R',2)
    time.sleep(.5)
finally:
    if proc is not None:
        os.killpg(proc.pid, signal.SIGTERM)
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL); proc.wait()
    xserver.terminate(); xserver.wait(timeout=5)
subprocess.run(['ffmpeg','-y','-v','error','-i',str(e/'audio.wav'),'-f','f32le','-ac','1','build/audio.f32'],check=True)
a=array.array('f'); a.frombytes((r/'build/audio.f32').read_bytes())
active=[i for i,v in enumerate(a) if abs(v)>.002]
assert active, 'No tone recorded'
first,last=active[0],active[-1]
# Positive-going crossings on a central one-second segment.
seg=a[first+24000:first+72000]
crossings=sum(seg[i-1]<=0<seg[i] for i in range(1,len(seg)))
report={'sprite_screen_bounds':positions,'all_four_directions_passed':True,'audio_sample_rate':48000,'audio_peak':max(abs(v) for v in a),'tone_active_duration_seconds':(last-first)/48000,'tone_estimated_hz':crossings*48000/len(seg),'host_audio_backend':'OpenAL wave file; no physical listening','minimum_machine_requirement_measured':False}
assert 250<report['tone_estimated_hz']<310, report
assert 1.7<report['tone_active_duration_seconds']<2.4, report
(e/'smoke-report.json').write_text(json.dumps(report,indent=2)+'\n')
# Keep a small playable capture as evidence, discard the long silent lead-in.
subprocess.run(['ffmpeg','-y','-v','error','-ss',str(max(0,first/48000-.25)),'-i',str(e/'audio.wav'),'-t',str((last-first)/48000+.5),'-c:a','pcm_s16le',str(e/'tone.wav')],check=True)
print(json.dumps(report,indent=2))
