#!/usr/bin/env python3
"""Export a checked linked RAM map; distinguish relocation from live addresses."""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--runtime-base',type=lambda x:int(x,0),help='Only supply a base observed from this running build')
    a=p.parse_args()
    prefix=next((x for x in ['m68k-elf-','m68k-linux-gnu-'] if shutil.which(x+'nm')),None)
    if prefix is None:p.error('m68k binutils required')
    data=a.elf.read_bytes()
    if data[:6]!=b'\x7fELF\x01\x02':p.error('Expected big-endian ELF32')
    shoff=struct.unpack_from('>I',data,32)[0]
    size,count,names=struct.unpack_from('>HHH',data,46)
    if size!=40:p.error('Unsupported ELF section header')
    sections=[struct.unpack_from('>10I',data,shoff+i*size) for i in range(count)]
    strings=data[sections[names][4]:sections[names][4]+sections[names][5]]
    symbols={};objects=[]
    for line in subprocess.check_output([prefix+'nm','-S','-n',str(a.elf)],text=True).splitlines():
        f=line.split()
        if len(f) not in (3,4):continue
        address=int(f[0],16);name=f[-1];symbols[name]=address
        if len(f)==4:objects.append(dict(name=name,linked_address=address,size_bytes=int(f[1],16),symbol_type=f[2]))
    base=symbols['_payload_base'];end=symbols['_end']
    def memory(address):
        if symbols['_chip_start']<=address<symbols['_chip_end']:return 'Chip'
        if base<=address<end:return 'Fast'
        return 'fixed/other'
    regions=[]
    for s in sections:
        if not s[2]&2 or not s[5]:continue
        name=strings[s[0]:strings.index(0,s[0])].decode()
        address=s[3];kind=memory(address)
        expected='Chip' if name=='.chipbuf' else 'Fast'
        if kind!=expected:raise SystemExit(f'Unexpected placement: {name} at {address:#x}')
        regions.append(dict(name=name,linked_address=address,size_bytes=s[5],memory=kind,
                            stored_in_payload=s[1]!=8,
                            runtime_address=(address if kind=='Chip' else address-base+a.runtime_base)
                                            if a.runtime_base is not None else None))
    for obj in objects:obj['memory']=memory(obj['linked_address'])
    required_fast=['nes','rt','rt_apu','tab_fix','tab_win0','cfgs','spr_sg','spr_sh','c2p1','c2p2',
                   'plat_isr_audio_c','plat_isr_vbl_c','plat_isr_ports_c','plat_isr_ciab_c']
    for name in required_fast:
        if name not in symbols or memory(symbols[name])!='Fast':raise SystemExit('CPU resource not in Fast: '+name)
    required_chip=['hwmem','cop','chunk','silence','plat_null_sprite']
    for name in required_chip:
        if name not in symbols or memory(symbols[name])!='Chip':raise SystemExit('DMA resource not in Chip: '+name)
    relocation_path=a.elf.parent/'reloc.json'
    reloc=json.loads(relocation_path.read_text()) if relocation_path.exists() else None
    payload=a.elf.with_suffix('.bin')
    staging=((payload.stat().st_size+511)//512)*512 if payload.exists() else None
    report=dict(scope='Linked layout checked against ELF; runtime addresses require a separately observed relocated base',
                cpu='stock 68EC020, instruction cache enabled by crt0; no data cache',
                linked_base=base,observed_runtime_base=a.runtime_base,
                runtime_fast_bytes=reloc['memory_bytes'] if reloc else end-base,
                chip_output_bytes=symbols['_chip_end']-symbols['_chip_start'],
                stack_bytes=symbols.get('_stack_size'),rom_bytes=262144,
                boot_chip_staging_bytes=staging,sections=regions,
                objects=sorted(objects,key=lambda o:-o['size_bytes']),
                findings=['CPU code, ROM, stack, dispatch tables, renderer metadata and interrupt handlers are in Fast RAM',
                          'Displayed bitmaps, Copper lists and Paula sample buffers are in Chip RAM',
                          'The bootloader requests MEMF_FAST dynamically; linked base is not a guaranteed load address',
                          'The boot staging allocation occurs before takeover; it is not added to steady-state buffers as if live simultaneously',
                          'OS/loader coexistence and physical expansion bus width are not measured by this static audit'])
    shadow=next((o for o in objects if o['name']=='hw_static'),None)
    if shadow:report['findings'].append(f'Redundant fallback hw_static reserves {shadow["size_bytes"]} Fast bytes although the player supplies Chip output buffers; candidate removal needs a separate check')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Linked memory map','',report['scope'],'',
           '| Resource | Linked address | Bytes | Type |','| --- | ---: | ---: | --- |']
    lines += [f'| {r["name"]} | ${r["linked_address"]:08X} | {r["size_bytes"]:,} | {r["memory"]} |' for r in regions]
    lines+=['','## Placement checks','']+['- '+s for s in report['findings']]
    lines+=['','## Large allocations and interrupt code','',
            '| Symbol | Linked address | Bytes | Type |','| --- | ---: | ---: | --- |']
    lines += [f'| {o["name"]} | ${o["linked_address"]:08X} | {o["size_bytes"]:,} | {o["memory"]} |'
              for o in report['objects'] if o['size_bytes']>=4096 or o['name'].startswith('plat_isr_')]
    a.output.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:report[k] for k in ['runtime_fast_bytes','chip_output_bytes','stack_bytes','boot_chip_staging_bytes','findings']},indent=2))


if __name__=='__main__':main()
