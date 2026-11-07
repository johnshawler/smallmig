#!/usr/bin/env python3
"""Actually execute original NES and Amiga fixtures on a display-free Linux runner."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/headless'


def nes_fixture():
    # Original mapper-0 test: the NMI handler increments RAM[0] once per frame.
    prg = bytearray([0xEA] * 16384)
    code = bytes.fromhex('78 d8 a2 ff 9a e8 8e 00 20 8e 01 20 86 00 2c 02 20 10 fb a9 80 8d 00 20 4c 18 80')
    prg[:len(code)] = code
    prg[0x80:0x83] = bytes.fromhex('e6 00 40')
    struct.pack_into('<HHH', prg, 0x3FFA, 0x8080, 0x8000, 0x8080)
    rom = OUT / 'original-nmi-fixture.nes'
    rom.write_bytes(b'NES\x1a' + bytes([1, 1]) + bytes(10) + prg + bytes(8192))
    lua = OUT / 'mesen.lua'
    lua.write_text('''local frame=0
local first=0
emu.addEventCallback(function()
 frame=frame+1
 if frame==120 then first=emu.read(0,emu.memType.nesInternalRam) end
 if frame==240 then
  local last=emu.read(0,emu.memType.nesInternalRam)
  local delta=(last-first)%256
  print('SMALLMIG_MESEN frames=240 nmi_delta='..delta)
  if delta~=120 then emu.stop(1) else emu.stop(0) end
 end
end,emu.eventType.endFrame)
''')
    binary = ROOT / '.tools/mesen-2.1.1/Mesen'
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
               LD_PRELOAD='/usr/lib/x86_64-linux-gnu/libstdc++.so.6',
               DOTNET_BUNDLE_EXTRACT_BASE_DIR=str(OUT/'dotnet'))
    command = [str(binary), '--testRunner', '--enableStdout', '--timeout=20', str(lua), str(rom)]
    r = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
    (OUT/'mesen.log').write_bytes(r.stdout)
    if r.returncode or b'SMALLMIG_MESEN frames=240 nmi_delta=120' not in r.stdout:
        raise RuntimeError('Mesen execution failed; see build/headless/mesen.log')
    return {'frames': 240, 'nmi_delta': 120, 'returncode': r.returncode,
            'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}


def amiga_fixture():
    # Add a test-only memory mailbox to the original native Small Mig smoke demo.
    source = (ROOT/'src/boot.s').read_text()
    assert source.count('\nframe:\n') == 1
    source = source.replace('\nframe:\n', '''
    move.l #0x534d4947,0x600
    clr.l 0x604
frame:
    addq.l #1,0x604
''')
    asm = OUT/'boot.s'
    asm.write_text(source)
    subprocess.run(['m68k-linux-gnu-as', '-m68020', '--register-prefix-optional', '-o', str(OUT/'boot.o'), str(asm)], check=True)
    subprocess.run(['m68k-linux-gnu-ld', '-Ttext=0', '-e', '_start', '--oformat=binary', '-o', str(OUT/'boot.raw'), str(OUT/'boot.o')], check=True)
    raw = (OUT/'boot.raw').read_bytes()
    assert 12 < len(raw) <= 1024
    block = bytearray(raw.ljust(1024, b'\0'))
    total = 0
    for (word,) in struct.iter_unpack('>I', block):
        total += word
        total = (total & 0xFFFFFFFF) + (total >> 32)
    struct.pack_into('>I', block, 4, (~total) & 0xFFFFFFFF)
    disk = OUT/'native-smoke.adf'
    disk.write_bytes(block + bytes(901120-1024))
    lua = OUT/'fs-uae.lua'
    # UAE's Lua state has only its explicit API, so no os/io/string libraries needed.
    lua.write_text('''function on_uae_vsync()
 if uae_read_u16(0x600)==0x534d and uae_read_u16(0x602)==0x4947 then
  local count=uae_read_u16(0x606)
  if count>=5 and count<=10 then uae_log('SMALLMIG_NATIVE frames='..count..'\\n') end
 end
end
''')
    base = OUT/'fs-uae'
    cfg = OUT/'native.fs-uae'
    cfg.write_text(f'''[fs-uae]
amiga_model = A1200
cpu = 68EC020
chip_memory = 2048
fast_memory = 8192
slow_memory = 0
kickstart_file = internal
floppy_drive_0 = {disk}
floppy_drive_speed = 0
floppy_drive_volume = 0
ntsc_mode = 0
video_sync = off
fullscreen = 0
automatic_input_grab = 0
uae_cachesize = 0
uae_cpu_speed = real
uae_cpu_cycle_exact = true
uae_cpu_memory_cycle_exact = true
uae_blitter_cycle_exact = true
uae_lua = {lua}
base_dir = {base}
log_flush = 1
''')
    env = dict(os.environ, LIBGL_ALWAYS_SOFTWARE='1', ALSOFT_DRIVERS='null', SDL_AUDIODRIVER='dummy')
    logpath = OUT/'fs-uae-console.log'
    logs = ''
    with logpath.open('wb') as log:
        proc = subprocess.Popen(['xvfb-run', '-a', '-s', '-screen 0 1024x768x24', 'fs-uae', str(cfg)],
                                env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic()+100
        try:
            while time.monotonic() < deadline:
                logs = logpath.read_text(errors='replace')
                if base.exists():
                    for p in base.rglob('*'):
                        if p.is_file() and p.name in ('fs-uae.log.txt', 'debug.uae'):
                            logs += p.read_text(errors='replace')
                if re.search(r'SMALLMIG_NATIVE frames=([5-9]|10)\b', logs):
                    break
                if proc.poll() is not None:
                    raise RuntimeError('FS-UAE exited before the native fixture ran')
                time.sleep(0.25)
            else:
                raise RuntimeError('FS-UAE did not report native frame progress within 100 seconds')
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
    return {'native_loop_frames': int(re.search(r'SMALLMIG_NATIVE frames=(\d+)', logs)[1]),
            'headless_backend': 'Xvfb / software Mesa', 'firmware': 'built-in AROS replacement',
            'profile': 'PAL A1200 68EC020, 2 MiB Chip + 8 MiB Fast, JIT disabled',
            'adf_sha256': hashlib.sha256(disk.read_bytes()).hexdigest()}


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'mesen': nes_fixture(), 'fs_uae': amiga_fixture(),
              'scope': 'Original installation fixtures, not Little League speed acceptance'}
    (OUT/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
