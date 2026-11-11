#!/usr/bin/env python3
"""Run the actual translated payload in a CPU-only 68020 reference core.

Needs an existing Musashi source directory. This is functional native-code
validation, not FS-UAE, Amiga DMA/audio playback, or physical speed acceptance.
Private inputs and generated binaries remain below ignored build directories.
"""
import argparse
import json
import os
import bisect
import csv
from pathlib import Path
import shutil
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = HERE/'vendor'


def symbols(path, prefix):
    result = {}
    for line in subprocess.check_output([prefix+'nm', '-n', str(path)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            result[fields[2]] = int(fields[0], 16)
    return result


def renderer_storage(game, sized_symbols):
    """Reject malformed/mismatched ELF storage before running native code."""
    address = game['hwmem']
    size = sized_symbols['hwmem']
    start, end = game['_chip_start'], game['_chip_end']
    # The player allocates AR_HW_BYTES + 4. Check the object, not a guessed
    # neighboring symbol. Preserve its DMA pad and reject low-memory aliases.
    if address & 3 or size < 8 or size & 3 or not 0x1000 <= start <= address < end <= 0x200000 or size > end-address:
        raise ValueError('Invalid native renderer Chip storage bounds/alignment')
    if not 0x200000 <= game['ar_hw_setmem'] < game['_load_end']:
        raise ValueError('Renderer setter outside loaded payload')
    return [game['ar_hw_setmem'], address, size]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--payload', required=True, type=Path, help='Existing private llb.elf, with patched llb.bin beside it')
    p.add_argument('--states', required=True, type=Path, help='Host STATEOUT checkpoints for the same input script')
    p.add_argument('--musashi', required=True, type=Path, help='Musashi C source directory')
    p.add_argument('--state-output', action='store_true', help='Record private native RAM/OAM/palette/nametable checkpoints')
    p.add_argument('--diagnose-mismatches', action='store_true', help='Continue collecting mismatches; still fail on any difference')
    p.add_argument('--wide-dma', action='store_true', help='Match an AR2_FETCH32 payload layout')
    p.add_argument('--frames', type=int, default=6000)
    p.add_argument('--profile', action='store_true', help='Attribute independent-core cycles to native functions')
    p.add_argument('--first', type=int, default=1600)
    p.add_argument('--last', type=int, default=2200)
    p.add_argument('--pcm', type=Path, help='Compare the complete native PAL PCM stream hash against this host PCMOUT file')
    p.add_argument('--script', type=Path, default=SRC/'tools/discovery/inputs/play_watchgame.txt')
    a = p.parse_args()
    if a.frames < 2:
        p.error('frames must be at least two')
    if a.profile and not 1<=a.first<a.last<=a.frames:
        p.error('Require 1 <= first < last <= frames for profiling')
    prefix = next((x for x in ['m68k-elf-', 'm68k-linux-gnu-'] if shutil.which(x+'gcc')), None)
    if not prefix:
        p.error('m68k GCC and binutils are required')
    out = ROOT/'build/little-league-original/native-check'/(a.payload.parent.name+'-'+str(a.frames))
    if a.profile:
        out = out.with_name(out.name+f'-profile-{a.first}-{a.last}')
    out.mkdir(parents=True, exist_ok=True)
    game = symbols(a.payload, prefix)
    if game['_payload_base'] != 0x200000:
        p.error('This runner expects a payload linked at 0x200000')
    lines = []
    for line in a.script.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2:
            lines.append('{%d,0x%x},' % (int(fields[0]), int(fields[1], 16)))
    (out/'testinput.inc').write_text('\n'.join(lines)+'\n')
    flags = ['-m68020', '-ffreestanding', '-nostdlib', '-fno-pic', '-O2', '-DAMIGA', '-DPPU_FB5',
             '-I'+str(SRC/'platform-a1200/freestanding'), '-I'+str(out)]
    if a.wide_dma:
        flags.append('-DAR2_FETCH32')
    subprocess.run([prefix+'gcc', *flags, '-c', str(SRC/'tools/native_hooks.c'), '-o', str(out/'hooks.o')], check=True)
    undefined = subprocess.check_output([prefix+'nm', '-u', str(out/'hooks.o')], text=True)
    defs = []
    for line in undefined.splitlines():
        name = line.split()[-1]
        if name not in game:
            raise SystemExit('Payload lacks native hook dependency: '+name)
        defs.append('--defsym='+name+'='+hex(game[name]))
    subprocess.run([prefix+'ld', '-z', 'noexecstack', '--no-warn-rwx-segments', '-Ttext=0xa00000',
                    '-e', 'native_init', *defs, '-o', str(out/'hooks.elf'), str(out/'hooks.o')], check=True)
    subprocess.run([prefix+'objcopy', '-O', 'binary', str(out/'hooks.elf'), str(out/'hooks.bin')], check=True)
    hooks = symbols(out/'hooks.elf', prefix)
    names = ['tabs_expand','rt_init','rom_start','xrt_run','rt','nes','ppu_ar_enable','ar_hw_enable','rt_fatal']
    addresses = [game[n] for n in names] + [hooks[n] for n in ['native_init','native_frame','native_input','native_layout','native_pcm_hash']]
    addresses.append(game.get('ar_sprite_cache_stats',0))
    sizes = {}
    for line in subprocess.check_output([prefix+'nm', '-S', str(a.payload)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 4:
            sizes[fields[3]] = int(fields[1], 16)
    addresses.extend(renderer_storage(game, sizes))
    addresses.append(hooks['native_hw_storage_bytes'])
    (out/'metadata.bin').write_bytes(struct.pack('>'+str(len(addresses))+'I', *addresses))
    data = a.states.read_bytes()
    if len(data) % 4392:
        p.error('Truncated STATEOUT input')
    records = [data[i:i+4392] for i in range(0, len(data), 4392)
               if struct.unpack_from('<Q', data, i)[0] < a.frames]
    if not records:
        p.error('No selected checkpoints before the requested final frame')
    (out/'states.bin').write_bytes(b''.join(records))
    musashi = a.musashi.resolve()
    cc = shutil.which('clang') or shutil.which('cc')
    # Generate opcode handlers in this run's own directory, without modifying the dependency.
    subprocess.run([cc, '-O2', str(musashi/'m68kmake.c'), '-o', str(out/'m68kmake')], check=True)
    subprocess.run([str(out/'m68kmake'), str(out), str(musashi/'m68k_in.c')], check=True)
    subprocess.run([cc, '-O2', '-DM68K_INSTRUCTION_HOOK=1', '-I'+str(out), '-I'+str(musashi), str(SRC/'tools/native_cpu.c'),
                    str(musashi/'m68kcpu.c'), str(out/'m68kops.c'), str(musashi/'softfloat/softfloat.c'),
                    '-lm', '-o', str(out/'native-cpu')], check=True)
    log = out/'result.log'
    env=os.environ.copy()
    for key in ('NATIVE_PROFILE','NATIVE_PROFILE_FIRST','NATIVE_PROFILE_LAST','NATIVE_STATEOUT','NATIVE_DIAGNOSE_MISMATCHES'):
        env.pop(key,None)
    if a.state_output:
        env['NATIVE_STATEOUT']=str(out/'native-states.bin')
    if a.diagnose_mismatches:
        env['NATIVE_DIAGNOSE_MISMATCHES']='1'
    if a.profile:
        env.update(NATIVE_PROFILE=str(out/'profile.csv'),NATIVE_PROFILE_FIRST=str(a.first),NATIVE_PROFILE_LAST=str(a.last))
    with log.open('w') as stream:
        result = subprocess.run([str(out/'native-cpu'), str(a.payload.with_suffix('.bin').resolve()),
                                 str(out/'hooks.bin'), str(out/'metadata.bin'), str(out/'states.bin'), str(a.frames)],
                                stdout=stream, stderr=subprocess.STDOUT, timeout=1800,env=env)
    print(log.read_text(), end='')
    if a.state_output and (out/'native-states.bin').stat().st_size != a.frames*4392:
        raise SystemExit('Incomplete native state output')
    if result.returncode:
        raise SystemExit(result.returncode)
    report = json.loads(log.read_text().splitlines()[-1])
    if report['native_frames'] != a.frames or report['checkpoints'] != len(records):
        raise SystemExit('Incomplete native execution')
    if a.pcm:
        data=a.pcm.read_bytes()
        pos=0
        for _ in range(a.frames):
            if pos+2>len(data):
                raise SystemExit('Reference PCM stream ended early')
            n=struct.unpack_from('>H',data,pos)[0]
            pos+=2+2*n
        if pos!=len(data):
            raise SystemExit('Reference PCM frame count or size differs')
        h=2166136261
        for b in data:
            h=((h^b)*16777619)&0xffffffff
        if h!=report['pcm_fnv32']:
            raise SystemExit(f'Native PCM mismatch: expected {h:08x}, got {report["pcm_fnv32"]:08x}')
        report['pcm_reference_hash_matched']=True
    (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    if a.profile:
        # The core has no Amiga memory contention. Retain cycles rather than
        # presenting these as stock A1200 milliseconds or game-speed percentages.
        functions={}
        for line in subprocess.check_output([prefix+'nm','-n',str(a.payload)],text=True).splitlines():
            fields=line.split()
            if len(fields)==3 and fields[1] in ('t','T') and not fields[2].startswith('_pr'):
                functions[int(fields[0],16)]=fields[2]
        starts=sorted(functions)
        grouped={}; categories={}; total=0
        edges=[game['_pr'+str(i)] for i in range(11)]
        labels=['translated','dispatch','helpers','time_model','PPU','interpreter_mapper','APU','renderer','platform_display','other']
        with (out/'profile.csv').open() as stream:
            for row in csv.DictReader(stream):
                pc=int(row['pc'],16); cycles=int(row['core_cycles']); total+=cycles
                i=bisect.bisect_right(starts,pc)-1
                name=functions[starts[i]] if i>=0 and pc<edges[-1] else 'test_hook'
                grouped[name]=grouped.get(name,0)+cycles
                i=bisect.bisect_right(edges,pc)-1
                category=labels[i] if 0<=i<len(labels) and pc<edges[-1] else 'test_hook'
                categories[category]=categories.get(category,0)+cycles
        result=dict(frame_window=[a.first,a.last],core_cycles=total,
                    core_cycles_per_frame=total/(a.last-a.first),
                    categories={k:dict(core_cycles=v,percent=100*v/total) for k,v in sorted(categories.items(),key=lambda x:-x[1])},
                    top_functions=[dict(name=k,core_cycles=v,percent=100*v/total) for k,v in sorted(grouped.items(),key=lambda x:-x[1])[:40]],
                    scope='CPU-only Musashi attribution, no Amiga bus contention or display DMA; test_hook includes PCM hashing absent from player')
        if not 0<total<=report['core_cycles']:
            raise SystemExit('Invalid native profile cycle accounting')
        (out/'profile.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
