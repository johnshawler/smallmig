#!/usr/bin/env python3
"""Compare guarded caller-owned rendering with fallback on original-game scripts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from build import cartridge, ROOT

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',required=True)
    p.add_argument('--frames',type=int,default=6000)
    a=p.parse_args()
    if a.frames<2: p.error('frames must be at least two')
    rom=cartridge(a.rom)
    out=ROOT/'build/little-league-external-storage/host-tests'
    out.mkdir(parents=True,exist_ok=True)
    cc=shutil.which('clang') or shutil.which('cc')
    runtime=['rt_core','cpu6502','ppu_ref','arender','mapper_mmc1','apu']
    env=os.environ.copy()
    for k in ('RT_NOFAST','PPU_REF','TRACECMP','FBDUMP','FBFRAMES','OAMDUMP','CMP_NOX','CMP_NO2002','ARDBG','ARDBG2','PREDICT_STRESS'):
        env.pop(k,None)
    env.update(PPU_CHECK='1',ARENDER='2',RT_LAZY='1',DRAWPAT='1',PCMSTD='pal')
    result=[]
    for variant in ('fallback','external'):
        subprocess.run([cc,'-O2','-DPPU_FB5','-DRT_AUDIO=1',*(['-DAR_NO_STATIC'] if variant=='external' else []),'-o',str(out/variant),str(HERE/'tests/external_storage_runner.c'),*[str(HERE/'vendor/runtime'/f'{r}.c') for r in runtime]],check=True)
    for script in ['play_watchgame',*[f'cov{i}' for i in range(1,9)]]:
        hashes={}
        for variant in ('fallback','external'):
            prefix=out/f'{script}-{variant}'
            paths={k:str(prefix.with_suffix(ext)) for k,ext in [('STATEOUT','.states'),('PCMOUT','.pcm')]}
            with prefix.with_suffix('.log').open('w') as f:
                subprocess.run([str(out/variant),str(rom),str(a.frames),str(HERE/'vendor/tools/discovery/inputs'/f'{script}.txt')],env={**env,**paths},stdout=f,stderr=subprocess.STDOUT,check=True)
            assert Path(paths['STATEOUT']).stat().st_size == a.frames*4392, (script,variant,'state length')
            hashes[variant]={k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in paths.items()}
        assert hashes['fallback']==hashes['external'],script
        result.append({'script':script,'frames':a.frames,'hashes':hashes['external']})
        print(script+': guarded storage, both layer sets, state/PCM identical',flush=True)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__': main()
