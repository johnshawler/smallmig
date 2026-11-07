#!/usr/bin/env python3
"""Check original-game PPU/planar equivalence and APU algorithms on the host."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
from build import HERE, ROOT, cartridge


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', required=True)
    p.add_argument('--frames', type=int, default=6000)
    p.add_argument('--draw-every', type=int, default=1)
    p.add_argument('--mesen', help='Also compare game RAM with this installed Mesen executable')
    p.add_argument('--mesen-timeout', type=int, default=120)
    a = p.parse_args()
    rom = cartridge(a.rom)
    if a.frames < 2 or a.draw_every < 1:
        p.error('frames must be at least 2; draw-every must be positive')
    out = ROOT/'build/little-league-original/checks'
    out.mkdir(parents=True, exist_ok=True)
    src = HERE/'vendor'
    cc = os.environ.get('CC') or shutil.which('clang') or shutil.which('cc')
    if not cc:
        raise SystemExit('A host C compiler is required')
    runtime = ['rt_core', 'cpu6502', 'ppu_ref', 'arender', 'mapper_mmc1', 'apu']
    subprocess.run([cc, '-O2', '-DPPU_FB5', '-DRT_AUDIO=1', '-Wno-unused', '-Wno-unknown-pragmas',
                    '-o', str(out/'rt-host'), 'tools/rt_host.c',
                    *['runtime/'+s+'.c' for s in runtime]], cwd=src, check=True)
    subprocess.run([cc, '-O2', '-o', str(out/'apu-test'), 'tests/apu_test.c', 'runtime/apu.c'], cwd=src, check=True)
    subprocess.run([str(out/'apu-test')], check=True)
    env = os.environ.copy()
    # Keep ambient test options from altering this check's scope or recording private data.
    for key in ('RT_NOFAST', 'PPU_REF', 'TRACECMP', 'FBDUMP', 'FBFRAMES', 'PCMOUT', 'OAMDUMP', 'STATEOUT',
                'CMP_NOX', 'CMP_NO2002', 'ARDBG', 'ARDBG2', 'PREDICT_STRESS'):
        env.pop(key, None)
    env.update(PPU_CHECK='1', ARENDER='2', RT_LAZY='1', DRAWPAT=str(a.draw_every))
    for script in ['play_watchgame', *['cov'+str(i) for i in range(1, 9)]]:
        log = out/(script+'.log')
        if a.mesen and script == 'play_watchgame':
            env['STATEOUT'] = str(out/'game-states.bin')
            env['FBFRAMES'] = ','.join(str(n-1) for n in sorted({n for n in (1500,6000,a.frames) if n<=a.frames}))
        else:
            env.pop('STATEOUT', None)
            env.pop('FBFRAMES', None)
        with log.open('w') as f:
            result = subprocess.run([str(out/'rt-host'), str(rom), str(a.frames),
                                     'tools/discovery/inputs/'+script+'.txt'], cwd=src,
                                    env=env, stdout=f, stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit(log.read_text()[-5000:])
        print(script+': '+next(line for line in log.read_text().splitlines() if line.startswith('ARENDER: ') and 'identical' in line))
    if a.mesen:
        from mesen_reference import capture, compare
        states = capture(Path(a.mesen).expanduser().resolve(), rom,
                         src/'tools/discovery/inputs/play_watchgame.txt', out, a.frames, a.mesen_timeout)
        compare(out/'game-states.bin', states)
    print('Passed requested reference checks. Native speed and complete gameplay acceptance remain separate.')


if __name__ == '__main__':
    main()
