#!/usr/bin/env python3
"""Pixel-check the real Copper renderer under headless FS-UAE, without game assets."""
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT/'ports/little-league/vendor'
OUT = ROOT/'build/headless-aga'
PREFIX = os.environ.get('M68K_PREFIX','m68k-linux-gnu-')


def run(command, **kw):
    return subprocess.run([str(x) for x in command], check=True, **kw)


def firmware(mode):
    out = OUT/str(mode)
    out.mkdir(parents=True, exist_ok=True)
    (out/'driver.c').write_text('''#include "display_ar2.h"
void display_init(void){}
void plat_isr_audio_c(void){ *(volatile unsigned short*)0xdff09c=0x180; }
void ar_hw_palette(const ArRegion*r,unsigned char*out){
 if(r->kind==AR_BLANK){for(int i=0;i<32;i++)out[i]=r->pal[r->blank_idx&31];return;}
 for(int i=0;i<32;i++)out[i]=(i&3)?r->pal[i]:r->pal[0];
}
extern void arhw_test_main(void);
void main(void){arhw_test_main();}
''')
    flags = ['-m68020','-ffreestanding','-nostdlib','-fno-pic','-O2','-fno-tree-loop-distribute-patterns',
             '-DAMIGA','-DPPU_FB5','-DARHW_STANDALONE','-I'+str(SRC/'platform-a1200'),
             '-I'+str(SRC/'platform-a1200/freestanding')]
    if mode==32:
        flags.append('-DAR2_FETCH32')
    objects=[]
    for name in ['platform','display_ar2','arhw_test','palette','libc']:
        obj=out/(name+'.o')
        run([PREFIX+'gcc',*flags,'-c',SRC/'platform-a1200'/(name+'.c'),'-o',obj])
        objects.append(obj)
    run([PREFIX+'gcc',*flags,'-c',out/'driver.c','-o',out/'driver.o'])
    objects.append(out/'driver.o')
    for name in ['crt0','isr']:
        obj=out/(name+'.o')
        run([PREFIX+'gcc','-m68020','-x','assembler','-c',SRC/'platform-a1200'/(name+'.s'),'-o',obj])
        objects.append(obj)
    libgcc=subprocess.check_output([PREFIX+'gcc','-m68020','-print-libgcc-file-name'],text=True).strip()
    run([PREFIX+'ld','-z','noexecstack','--no-warn-rwx-segments','-T',SRC/'platform-a1200/link.ld',
         '-o',out/'fixture.elf',*objects,libgcc])
    run([PREFIX+'objcopy','-O','binary',out/'fixture.elf',out/'fixture.bin'])
    data=(out/'fixture.bin').read_bytes()
    (out/'reset.s').write_text(f'''.text
 .long 0x1ff000,0xf80008
 move.w #0x2700,%sr
 move.b #3,0xbfe201
 bclr #0,0xbfe001
 lea image(%pc),%a0
 lea 0x800,%a1
 move.l #{(len(data)+3)//4-1},%d0
copy:
 move.l (%a0)+,(%a1)+
 subq.l #1,%d0
 bpl copy
 jmp 0x800
 .balign 4
image:
 .incbin "{out/'fixture.bin'}"
 .balign 4
''')
    run([PREFIX+'as','-m68020','--register-prefix-optional',out/'reset.s','-o',out/'reset.o'])
    run([PREFIX+'ld','-Ttext=0xf80000','--oformat=binary','-o',out/'reset.bin',out/'reset.o'])
    reset=(out/'reset.bin').read_bytes()
    assert len(reset)<524288-24
    rom=bytearray(reset.ljust(524288,b'\xff'))
    struct.pack_into('>I',rom,len(rom)-24,0)
    total=0
    for (w,) in struct.iter_unpack('>I',rom):
        total+=w;total=(total&0xffffffff)+(total>>32)
    struct.pack_into('>I',rom,len(rom)-24,(~total)&0xffffffff)
    (out/'fixture.rom').write_bytes(rom)
    return out


def execute(out):
    base=out/'fs-uae'
    config=out/'fixture.fs-uae'
    config.write_text(f'''[fs-uae]
amiga_model = A1200
cpu = 68EC020
chip_memory = 2048
fast_memory = 8192
slow_memory = 0
kickstart_file = {out/'fixture.rom'}
base_dir = {base}
screenshots_output_dir = {out}
keyboard_key_f10 = action_screenshot
fullscreen = 0
automatic_input_grab = 0
video_sync = off
ntsc_mode = 0
uae_cachesize = 0
uae_cpu_speed = real
uae_cpu_cycle_exact = true
uae_cpu_memory_cycle_exact = true
uae_blitter_cycle_exact = true
uae_log_illegal_mem = true
log_flush = 1
''')
    env=dict(os.environ,LIBGL_ALWAYS_SOFTWARE='1',ALSOFT_DRIVERS='null',SDL_AUDIODRIVER='dummy')
    with (out/'console.log').open('w') as log:
        proc=subprocess.Popen(['fs-uae',str(config)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                text=(out/'console.log').read_text(errors='replace')
                for p in base.rglob('*'):
                    if p.is_file() and p.name in ['fs-uae.log.txt','debug.uae']:
                        text+=p.read_text(errors='replace')
                if '00d00000=0000534d' in text:
                    break
                if proc.poll() is not None:
                    raise RuntimeError('FS-UAE exited before the Copper fixture was ready')
                time.sleep(.25)
            else:
                raise RuntimeError('Copper fixture did not become ready within 120 seconds')
            ids=subprocess.check_output(['xdotool','search','--onlyvisible','--name','FS-UAE'],text=True).splitlines()
            if not ids:
                raise RuntimeError('No virtual FS-UAE window')
            run(['xdotool','windowfocus',ids[0]])
            run(['xdotool','key','F10'])
            deadline=time.monotonic()+10
            while time.monotonic()<deadline:
                files=list(out.glob('fs-uae-full-*.png'))
                if files:
                    run([sys.executable,SRC/'tests/amiga/arhw_expect.py',files[-1],'pal'])
                    return
                time.sleep(.1)
            raise RuntimeError('FS-UAE did not save the native framebuffer')
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait()


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--inside':
        execute(Path(sys.argv[2]))
    else:
        for mode in [16,32]:
            out=firmware(mode)
            run(['xvfb-run','-a','-s','-screen 0 1024x768x24',sys.executable,__file__,'--inside',out])
