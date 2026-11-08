#!/usr/bin/env python3
"""Run the supplied ROM in Mesen's documented test runner; retain local evidence."""
import hashlib,json,pathlib,shutil,subprocess
H=pathlib.Path(__file__).resolve().parent;R=H.parents[1];S=R/'build/little-league/source'
ROM_SHA='f33ee3c2cdf4cb23bb060574234fa6ebb45ac0c7dea1f910d1b86c0e42990c23'
def capture(rom,mesen=None):
 rom=pathlib.Path(rom).resolve();digest=hashlib.sha256(rom.read_bytes()).hexdigest()
 if digest!=ROM_SHA:raise SystemExit('This initial capture script expects the verified USA cartridge revision: '+ROM_SHA)
 exe=mesen or shutil.which('Mesen')
 if not exe and pathlib.Path('/Applications/Mesen.app/Contents/MacOS/Mesen').is_file():exe='/Applications/Mesen.app/Contents/MacOS/Mesen'
 if not exe:raise SystemExit('Supply --mesen /path/to/Mesen for reference capture')
 S.mkdir(parents=True,exist_ok=True)
 args=[exe,'--testRunner','--enableStdout','--timeout=30','--nes.port1.type=NesController',str(H/'reference.lua'),str(rom)]
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
 (S/'reference.log').write_bytes(p.stdout)
 if p.returncode:raise SystemExit('Mesen reference run failed; inspect build/little-league/source/reference.log')
 for line in p.stdout.decode(errors='replace').splitlines():
  if line.startswith(('PPU ','OAM ','RGB ','PNG ')):
   kind,frame,data=line.split();suffix='.png' if kind=='PNG' else '.bin';(S/(kind+'-'+frame+suffix)).write_bytes(bytes.fromhex(data))
 for frame in [2400,3300]:
  for kind,size in [('PPU',16384),('OAM',256),('RGB',184320)]:
   if (S/f'{kind}-{frame}.bin').stat().st_size!=size:raise SystemExit('Incomplete reference snapshot')
 report={'rom_sha256':digest,'source_frames':3600,'source_emulator':str(exe),'return_code':p.returncode,'scope':'Exhibition menus, team selection, batting view, CPU pitch flight. No stress or complete-game acceptance.'}
 (S/'reference-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--rom',required=True);a.add_argument('--mesen');v=a.parse_args();capture(v.rom,v.mesen)
