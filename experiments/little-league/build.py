#!/usr/bin/env python3
"""Build a native Amiga batting slice using Small Mig's bootable ADF protocol."""
import argparse,hashlib,json,pathlib,shutil,struct,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[2];H=pathlib.Path(__file__).resolve().parent;O=R/'build/little-league'
sys.path.insert(0,str(H));from reference import capture,ROM_SHA
from reference_assets import extract

def build(rom,mesen=None,refresh=False,replay=False):
 digest=hashlib.sha256(pathlib.Path(rom).read_bytes()).hexdigest()
 if digest!=ROM_SHA:raise SystemExit('Unsupported ROM revision: '+digest)
 if refresh or not (O/'source/reference-report.json').exists():capture(rom,mesen)
 report=json.loads((O/'source/reference-report.json').read_text())
 if report['rom_sha256']!=digest:raise SystemExit('Reference snapshot belongs to a different ROM')
 extract()
 def tool(name,*args):
  exe=shutil.which('m68k-elf-'+name) or shutil.which('m68k-linux-gnu-'+name)
  if not exe:raise SystemExit('Missing m68k binutils/GCC: '+name)
  return subprocess.check_output([exe,*map(str,args)],cwd=R)
 tool('gcc',*(['-DSM_REPLAY'] if replay else []),'-m68020','-O2','-ffreestanding','-fno-builtin','-fomit-frame-pointer','-Wall','-Wextra','-I',O,'-c',H/'game.c','-o',O/'game.o')
 tool('as','-m68020','-o',O/'start.o',H/'start.s')
 tool('ld','-T',H/'link.ld','-o',O/'game.elf',O/'start.o',O/'game.o')
 tool('objcopy','-O','binary',O/'game.elf',O/'game.raw')
 tool('as','-m68020','-o',O/'loader.o',H/'loader.s')
 tool('ld','-Ttext=0','-e','_start','-o',O/'loader.elf',O/'loader.o')
 tool('objcopy','-O','binary',O/'loader.elf',O/'loader.raw')
 payload=(O/'game.raw').read_bytes();loader=(O/'loader.raw').read_bytes();assert len(payload)<=65536 and len(loader)<=1024
 block=bytearray(loader.ljust(1024,b'\0'));s=0
 for (w,) in struct.iter_unpack('>I',block):s+=w;s=(s&0xffffffff)+(s>>32)
 struct.pack_into('>I',block,4,(~s)&0xffffffff)
 checksum=0
 for (word,) in struct.iter_unpack('>I',block):
  checksum+=word;checksum=(checksum&0xffffffff)+(checksum>>32)
 assert checksum==0xffffffff,hex(checksum)
 disk=(block+payload.ljust(65536,b'\0')).ljust(901120,b'\0');(O/('Little-League-SmallMig-Replay.adf' if replay else 'Little-League-SmallMig-Batting.adf')).write_bytes(disk)
 (O/'game.disassembly.txt').write_bytes(tool('objdump','-d',O/'game.elf'))
 (O/'symbols.txt').write_bytes(tool('nm','-n',O/'game.elf'))
 report={'payload_bytes':len(payload),'adf_bytes':len(disk),'sha256':hashlib.sha256(disk).hexdigest(),'rom_sha256':hashlib.sha256(pathlib.Path(rom).read_bytes()).hexdigest(),'chip_reservation_bytes':262144,'fast_allocation_bytes':0,'target':'PAL A1200 68EC020 AGA','implementation':'Native batting prototype using ROM graphics reconstructed from a Mesen PPU/OAM capture. Not translated NES gameplay.'}
 report['replay']=replay
 report['boot_checksum']=hex(checksum)
 (O/('replay-build-report.json' if replay else 'build-report.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--rom',required=True);p.add_argument('--mesen');p.add_argument('--refresh-reference',action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args();build(a.rom,a.mesen,a.refresh_reference,a.replay)
