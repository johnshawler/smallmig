#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
import hashlib,json,os,pathlib,struct,subprocess
import falling
R=falling.ROOT; O=falling.OUT
report=falling.prepare()
env=dict(os.environ,LD_LIBRARY_PATH=str(R/'.tools/usr/lib/x86_64-linux-gnu'))
def tool(name,*args):
 p=subprocess.run([str(R/'.tools/usr/bin'/('m68k-linux-gnu-'+name)),*args],env=env,cwd=R,capture_output=True)
 if p.returncode:raise RuntimeError(p.stderr.decode())
 return p.stdout
for name in ['payload','loader']:
 tool('as','-m68020','-o',str(O/(name+'.o')),str(falling.HERE/(name+'.s')))
 tool('ld','-Ttext=0','-e','_start','-o',str(O/(name+'.elf')),str(O/(name+'.o')))
 tool('objcopy','-O','binary',str(O/(name+'.elf')),str(O/(name+'.raw')))
 (O/(name+'.disassembly.txt')).write_bytes(tool('objdump','-d',str(O/(name+'.elf'))))
symbols={}
for line in tool('nm',str(O/'payload.elf')).decode().splitlines():
 p=line.split()
 if len(p)==3:symbols[p[2]]=int(p[0],16)
payload=(O/'payload.raw').read_bytes();loader=(O/'loader.raw').read_bytes()
assert len(loader)<=1024 and len(payload)<=65536
block=bytearray(loader.ljust(1024,b'\0'));s=0
for (w,) in struct.iter_unpack('>I',block):
 s+=w;s=(s&0xffffffff)+(s>>32)
struct.pack_into('>I',block,4,(~s)&0xffffffff)
disk=block+payload.ljust(65536,b'\0');disk+=bytes(901120-len(disk))
(O/'falling-slice.adf').write_bytes(disk)
report.update({'translated_native_bytes':symbols['translated_falling_end']-symbols['translated_falling_move'],'payload_bytes':len(payload),'loader_bytes':len(loader),'explicit_chip_allocation_bytes':98304,'explicit_fast_allocation_bytes':0,'adf_sha256':hashlib.sha256(disk).hexdigest()})
(O/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('BUILD',json.dumps(report,indent=2))
