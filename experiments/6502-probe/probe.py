#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Original, deliberately restricted 6502 assembler/model/static translator.
Not an NES emulator, decompiler, or general 6502 translator. Rejects unknown opcodes.
"""
import hashlib, json, pathlib, struct, subprocess, os
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT/'build/probe'
EVIDENCE = ROOT/'evidence/probe'
OPS = {('LDA','zp'):0xA5, ('LDA','imm'):0xA9, ('CLC','none'):0x18,
       ('ADC','zp'):0x65, ('STA','zp'):0x85, ('CMP','zp'):0xC5,
       ('BNE','rel'):0xD0, ('INC','zp'):0xE6, ('RTS','none'):0x60}

def assemble(text):
    labels={}; instructions=[]; pc=0x8000
    for line in text.splitlines():
        line=line.split(';')[0].strip()
        if not line: continue
        if line.startswith('.org'):
            assert line.split()[1]=='$8000'; continue
        if line.endswith(':'): labels[line[:-1]]=pc; continue
        op,*rest=line.split(); arg=rest[0] if rest else ''
        mode='none' if not arg else 'rel' if op=='BNE' else 'imm' if arg.startswith('#') else 'zp'
        opcode=OPS[op,mode]; instructions.append((pc,opcode,arg,mode)); pc+=1+(mode!='none')
    code=bytearray()
    for pc,op,arg,mode in instructions:
        code.append(op)
        if mode!='none':
            value=labels[arg]-(pc+2) if mode=='rel' else int(arg.lstrip('#$'),16)
            assert -128<=value<=255
            code.append(value&255)
    return bytes(code)

def reference(code, initial):
    """Instruction-stepping model; independent of generated native code."""
    mem=bytearray(256); mem[:5]=bytes(initial)
    pc=0; a=c=z=n=v=0; count=0; visited=[]
    while True:
        assert 0<=pc<len(code); at=pc; op=code[pc]; pc+=1; count+=1; visited.append(at)
        assert count<100
        if op in (0xA5,0xA9):
            arg=code[pc]; pc+=1; a=mem[arg] if op==0xA5 else arg
            z=int(a==0); n=a>>7
        elif op==0x18: c=0
        elif op==0x65:
            b=mem[code[pc]]; pc+=1; old=a; total=a+b+c; a=total&255
            c=int(total>255); z=int(a==0); n=a>>7
            v=int((~(old^b)&(old^a)&128)!=0)
        elif op==0x85: mem[code[pc]]=a; pc+=1
        elif op==0xC5:
            b=mem[code[pc]]; pc+=1; d=(a-b)&255
            c=int(a>=b); z=int(a==b); n=d>>7
        elif op==0xD0:
            offset=code[pc]; pc+=1
            if not z: pc+=offset if offset<128 else offset-256
        elif op==0xE6:
            addr=code[pc]; pc+=1; mem[addr]=(mem[addr]+1)&255
            z=int(mem[addr]==0); n=mem[addr]>>7
        elif op==0x60:
            return list(mem[:5])+[a,c,z,n,v],count,set(visited)
        else: raise ValueError(f'Unsupported reference opcode {op:02x}')

def oracle(initial):
    """Mathematical expected answer for this particular program, no opcodes."""
    x,delta,wall,score,_=initial
    position=(x+delta)%256; hit=int(position==wall)
    result_score=(score+hit)%256
    # Signed overflow iff mathematical signed sum does not fit an int8.
    signed=lambda b:b if b<128 else b-256
    overflow=int(not -128<=signed(x)+signed(delta)<=127)
    return [position,delta,wall,result_score,hit,hit,int(position>=wall),
            int(result_score==0) if hit else 1,
            result_score>>7 if hit else 0,overflow]

def translate(code):
    """Decode ROM bytes once into labeled native instructions. No dispatch runtime.
    D0=A, D1=C, D2=Z, D3=N, D4=V; A3=256-byte zero-page backing store.
    D5-D7 are scratch. No cycle, IRQ, stack, decimal, or memory-mapped I/O model.
    RTS means return from this one statically translated entry point.
    """
    def zn(reg):
        return [f'    tst.b {reg}', '    seq %d2','    and.l #1,%d2',
                f'    move.l {reg},%d3','    lsr.l #7,%d3','    and.l #1,%d3']
    lines=['/* SPDX-License-Identifier: 0BSD; generated from move6502.bin */','translated_step:']
    pc=0; boundaries=set(); branches=[]
    while pc<len(code):
        at=pc; boundaries.add(at); op=code[pc]; pc+=1
        lines += [f'L6502_{at:04x}: /* ${0x8000+at:04x}: {op:02x} */']
        if op in (0xA5,0xA9,0x65,0x85,0xC5,0xD0,0xE6):
            arg=code[pc]; pc+=1
        if op in (0xA5,0xA9):
            lines += [f'    move.b {str(arg)+"(%a3)" if op==0xA5 else "#"+str(arg)},%d0','    and.l #255,%d0']+zn('%d0')
        elif op==0x18: lines+=['    moveq #0,%d1']
        elif op==0x65:
            lines += ['    move.l %d0,%d7', '    moveq #0,%d5',f'    move.b {arg}(%a3),%d5',
                      '    add.l %d5,%d0','    add.l %d1,%d0','    move.l %d0,%d1','    lsr.l #8,%d1',
                      '    and.l #255,%d0','    move.l %d7,%d4','    eor.l %d0,%d4',
                      '    move.l %d5,%d6','    eor.l %d0,%d6','    and.l %d6,%d4',
                      '    lsr.l #7,%d4','    and.l #1,%d4']+zn('%d0')
        elif op==0x85: lines += [f'    move.b %d0,{arg}(%a3)']
        elif op==0xC5:
            lines += [f'    cmp.b {arg}(%a3),%d0','    scc %d1','    and.l #1,%d1',
                      '    move.l %d0,%d5',f'    sub.b {arg}(%a3),%d5']+zn('%d5')
        elif op==0xD0:
            dest=pc+(arg if arg<128 else arg-256); branches.append(dest)
            lines += ['    tst.l %d2',f'    beq L6502_{dest:04x}']
        elif op==0xE6:
            lines += [f'    addq.b #1,{arg}(%a3)','    moveq #0,%d5',f'    move.b {arg}(%a3),%d5']+zn('%d5')
        elif op==0x60: lines += ['    rts']
        else: raise ValueError(f'Unsupported translator opcode {op:02x}')
    assert all(x in boundaries for x in branches), 'Branch into operand or out of program'
    return '\n'.join(lines)+'\n'

def fixtures():
    # Broad arithmetic values, exact-hit and no-hit branches, score wrap and sign.
    cases=[]
    for x in (0,1,2,63,64,126,127,128,129,191,254,255):
        for delta in (0,1,2,127,128,254,255):
            for hit in (False,True):
                wall=((x+delta)+(0 if hit else 1))&255
                cases.append([x,delta,wall,(x^delta)&255,0xA5])
    for score in (0,1,126,127,128,254,255):
        cases += [[9,1,10,score,0],[11,255,10,score,0]]
    # Actual sequential movement/contact demo, propagated between frames.
    state=[8,1,10,0,0]
    for delta in [1,1,1,255,255,1,1,0]:
        state[1]=delta; cases.append(state.copy()); state=oracle(state)[:5]
    return cases

def build(negative=False):
    OUT.mkdir(parents=True,exist_ok=True); EVIDENCE.mkdir(parents=True,exist_ok=True)
    code=assemble((HERE/'move6502.s').read_text())
    (OUT/'move6502.bin').write_bytes(code)
    (OUT/'translated.s').write_text(translate(code))
    visited=set(); total=0
    for x in range(256):
        for delta in range(256):
            for hit in (False,True):
                initial=[x,delta,(x+delta+(0 if hit else 1))&255,(x^delta)&255,0xA5]
                got,n,covered=reference(code,initial)
                assert got==oracle(initial),(initial,got,oracle(initial))
                visited|=covered; total+=1
    cases=fixtures(); expected=[]
    rows=bytearray()
    for initial in cases:
        answer,n,_=reference(code,initial)
        expected+=answer
        rows.extend(initial+answer)
    if negative: rows[5]^=1
    (OUT/'fixtures.bin').write_bytes(rows)
    (OUT/'expected-output.bin').write_bytes(bytes(expected))
    report={'source_license':'0BSD; original code','program_bytes':len(code),'program_sha256':hashlib.sha256(code).hexdigest(),
            'supported_opcodes':sorted(f'{x:02x}' for x in set(OPS.values())),
            'host_reference_vs_math_cases':total,'host_instruction_addresses_exercised':len(visited),
            'target_fixture_count':len(cases),'output_bytes_per_case':10,
            'output_fields':['x','delta','wall','score','hit','A','C','Z','N','V'],
            'negative_control':negative,'benchmark_iterations':20000}
    (OUT/'fixture-metadata.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'fixture-count.i').write_text(f'.equ CASE_COUNT,{len(cases)}\n')
    env=dict(os.environ,LD_LIBRARY_PATH=str(ROOT/'.tools/usr/lib/x86_64-linux-gnu'))
    def tool(name,*args):
        result=subprocess.run([str(ROOT/'.tools/usr/bin'/('m68k-linux-gnu-'+name)),*args],cwd=ROOT,env=env,capture_output=True)
        if result.returncode: raise RuntimeError(result.stderr.decode())
        return result.stdout
    for name in ('payload','loader'):
        tool('as','-m68020','-o',str(OUT/f'{name}.o'),str(HERE/f'{name}.s'))
        tool('ld','-Ttext=0','-e','_start','-o',str(OUT/f'{name}.elf'),str(OUT/f'{name}.o'))
        tool('objcopy','-O','binary',str(OUT/f'{name}.elf'),str(OUT/f'{name}.raw'))
        (OUT/f'{name}.disassembly.txt').write_bytes(tool('objdump','-d',str(OUT/f'{name}.elf')))
    symbols={}
    for line in tool('nm',str(OUT/'payload.elf')).decode().splitlines():
        parts=line.split()
        if len(parts)==3: symbols[parts[2]]=int(parts[0],16)
    report['translated_native_bytes']=symbols['translated_end']-symbols['translated_step']
    payload=(OUT/'payload.raw').read_bytes(); loader=(OUT/'loader.raw').read_bytes()
    assert len(loader)<=1024 and len(payload)<=16384
    block=bytearray(loader.ljust(1024,b'\0')); s=0
    for (w,) in struct.iter_unpack('>I',block):
        s+=w; s=(s&0xffffffff)+(s>>32)
    struct.pack_into('>I',block,4,(~s)&0xffffffff)
    disk=block+payload.ljust(16384,b'\0'); disk+=bytes(901120-len(disk))
    name='negative.adf' if negative else 'probe.adf'
    (OUT/name).write_bytes(disk)
    report.update({'payload_bytes':len(payload),'loader_bytes':len(loader),'explicit_chip_allocation_bytes':32768,
                   'explicit_fast_allocation_bytes':0,'adf_sha256':hashlib.sha256(disk).hexdigest()})
    (OUT/('negative-build.json' if negative else 'build-report.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':
    import sys
    build('--negative' in sys.argv)
