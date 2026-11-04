#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Small Mig: selected actual Falling ROM instructions -> native 68k.
Original adapter/tool code; upstream ROM-derived material remains MIT licensed.
"""
import hashlib,json,pathlib,re
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]
OUT=ROOT/'build/homebrew'; E=ROOT/'evidence/homebrew'
UP=HERE/'references/falling'
REV='52dcb8a951200562e696dfc2aba5d4d14edd0078'
ROM_SHA='e22b947542c2d7e595bf84725b333be7af8189c5965b9c53e356a249c7d79943'
FIELDS=['buttons','difficulty','playerx','playery','playerx_sub','playerfacing','obst1_update','obst2_update','obst3_update']
LENGTH={0xa9:2,0x8d:3,0x2c:3,0xf0:2,0xae:3,0xad:3,0x38:1,0xfd:3,0xb0:2,0xce:3,0x18:1,0x7d:3,0x90:2,0xee:3,0xc9:2,0x4c:3}

def load():
 s=(UP/'source/falling.asm').read_text(); sy={};pos=0
 for line in s[:s.index(';; DECLARE CONSTANTS')].splitlines():
  m=re.match(r'\s*(\w+)\s+\.rs\s+(\d+)',line)
  if m:sy[m[1]]=pos;pos+=int(m[2])
 rom=(UP/'falling.nes').read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 assert rom[:8]==bytes.fromhex('4e45531a02010000')
 prg=rom[16:32784];chr=rom[32784:]
 assert chr==(UP/'source/falling.chr').read_bytes()
 pattern=b'\xa9\x00'+b''.join(bytes([0x8d,sy[k],0]) for k in ['obst1_update','obst2_update','obst3_update'])
 assert prg.count(pattern)==1
 entry=prg.index(pattern)+0x8000; pc=entry;ins=[]
 while True:
  op=prg[pc-0x8000];n=LENGTH[op];raw=prg[pc-0x8000:pc-0x8000+n]
  arg=int.from_bytes(raw[1:],'little');ins.append((pc,op,arg));pc+=n
  if op==0x4c:break
 assert entry==0xc6c6 and pc==0xc754 and ins[-1][2]==0xc7ed
 boundaries={p for p,op,a in ins}
 for p,op,a in ins:
  if op in [0xf0,0xb0,0x90]:assert p+2+(a if a<128 else a-256) in boundaries
  if op in [0x8d,0x2c,0xae,0xad,0xce,0xee]:assert a<256
 assert {a for p,op,a in ins if op in [0xfd,0x7d]}=={0xda35,0xda6a}
 # Source table content validates correspondence; actual translation reads PRG.
 for label,addr in [('diff_playerspeed',0xda35),('diff_playerspeed_sub',0xda6a)]:
  chunk=re.split(r'(?m)^\w+:',s.split(label+':',1)[1],maxsplit=1)[0];vals=[]
  for line in chunk.splitlines():
   clean=line.split(';')[0]
   if '.db' in clean:vals.extend(int(x.strip()) for x in clean.split('.db')[1].split(','))
  assert bytes(vals)==prg[addr-0x8000:addr-0x8000+len(vals)] and len(vals)==53
 return sy,prg,chr,entry,pc,ins

def reference(initial,sy,prg,entry,ins):
 mem=bytearray(257)
 for k,v in zip(FIELDS,initial):mem[sy[k]]=v
 mem[256]=initial[9];a=c=z=n=v=0;pc=entry;by_pc={p:(op,arg) for p,op,arg in ins};visited=set()
 def read(addr):return mem[addr] if addr<256 else prg[addr-0x8000]
 while True:
  visited.add(pc);op,arg=by_pc[pc];pc+=LENGTH[op]
  if op in [0xa9,0xad]:
   a=arg if op==0xa9 else read(arg);z=int(a==0);n=a>>7
  elif op==0xae:mem[256]=read(arg);z=int(mem[256]==0);n=mem[256]>>7
  elif op==0x8d:mem[arg]=a
  elif op==0x2c:
   b=read(arg);z=int((a&b)==0);n=(b>>7)&1;v=(b>>6)&1
  elif op==0x18:c=0
  elif op==0x38:c=1
  elif op in [0x7d,0xfd]:
   b=read((arg+mem[256])&65535);old=a
   t=a+b+c if op==0x7d else a-b-(1-c)
   a=t&255;c=int(t>255) if op==0x7d else int(t>=0)
   v=int((~(old^b)&(old^a)&128)!=0) if op==0x7d else int(((old^b)&(old^a)&128)!=0)
   z=int(a==0);n=a>>7
  elif op in [0xce,0xee]:
   mem[arg]=(mem[arg]+(1 if op==0xee else -1))&255;z=int(mem[arg]==0);n=mem[arg]>>7
  elif op==0xc9:c=int(a>=arg);d=(a-arg)&255;z=int(d==0);n=d>>7
  elif op in [0xf0,0xb0,0x90]:
   if {0xf0:bool(z),0xb0:bool(c),0x90:not c}[op]:pc+=arg if arg<128 else arg-256
  elif op==0x4c:
   return [mem[sy[k]] for k in FIELDS]+[a,c,z,n,v,mem[256]],visited
  else:raise ValueError(op)

def oracle(initial,prg):
 b,d,x,y,sub,face,*flags=initial[:9];speed=prg[0xda35-0x8000+d];frac=prg[0xda6a-0x8000+d]
 if b&2:
  x=(x-speed-(sub<frac))&255;sub=(sub-frac)&255;face=0
 if b&1:
  carry=sub+frac>255;x=(x+speed+carry)&255;sub=(sub+frac)&255;face=1
 return [b,d,max(13,min(246,x)),max(40,min(160,y)),sub,face,0,0,0]

def translate(ins):
 def zn(reg):return [f'    tst.b {reg}','    seq %d2','    and.l #1,%d2',f'    move.l {reg},%d3','    lsr.l #7,%d3','    and.l #1,%d3']
 s=['/* ROM-derived native code. Falling Copyright (c) 2018 tragicmuffin; MIT. */','translated_falling_move:','    lea rom_prg(%pc),%a6']
 for pc,op,arg in ins:
  s += [f'F_{pc:04x}: /* original ROM ${pc:04x}, opcode ${op:02x} */']
  if op in [0xa9,0xad]:s += [f'    move.b {"#"+str(arg) if op==0xa9 else str(arg)+"(%a3)"},%d0','    and.l #255,%d0']+zn('%d0')
  elif op==0xae:s+=['    moveq #0,%d5',f'    move.b {arg}(%a3),%d5','    move.b %d5,256(%a3)']+zn('%d5')
  elif op==0x8d:s += [f'    move.b %d0,{arg}(%a3)']
  elif op==0x2c:
   s += ['    moveq #0,%d5',f'    move.b {arg}(%a3),%d5','    move.l %d0,%d6','    and.l %d5,%d6','    tst.b %d6','    seq %d2','    and.l #1,%d2','    move.l %d5,%d3','    lsr.l #7,%d3','    and.l #1,%d3','    move.l %d5,%d4','    lsr.l #6,%d4','    and.l #1,%d4']
  elif op in [0x18,0x38]:s += [f'    moveq #{int(op==0x38)},%d1']
  elif op in [0x7d,0xfd]:
   s += ['    move.l %d0,%d7','    moveq #0,%d5','    move.b 256(%a3),%d5','    moveq #0,%d6',f'    move.b {arg-0x8000}(%a6,%d5.l),%d6','    move.l %d6,%d5']
   if op==0x7d:s+=['    add.l %d5,%d0','    add.l %d1,%d0','    move.l %d0,%d1','    lsr.l #8,%d1']
   else:s+=['    sub.l %d5,%d0','    add.l %d1,%d0','    subq.l #1,%d0','    tst.l %d0','    spl %d1','    and.l #1,%d1']
   s+=['    and.l #255,%d0','    move.l %d7,%d4','    eor.l %d0,%d4',f'    move.l %{"d5" if op==0x7d else "d7"},%d6',f'    eor.l %{"d0" if op==0x7d else "d5"},%d6','    and.l %d6,%d4','    lsr.l #7,%d4','    and.l #1,%d4']+zn('%d0')
  elif op in [0xce,0xee]:s += [f'    {"addq" if op==0xee else "subq"}.b #1,{arg}(%a3)','    moveq #0,%d5',f'    move.b {arg}(%a3),%d5']+zn('%d5')
  elif op==0xc9:s += [f'    cmp.b #{arg},%d0','    scc %d1','    and.l #1,%d1','    move.l %d0,%d5',f'    sub.b #{arg},%d5']+zn('%d5')
  elif op in [0xf0,0xb0,0x90]:
   target=pc+2+(arg if arg<128 else arg-256)
   s += [f'    tst.l %{"d2" if op==0xf0 else "d1"}',f'    {"beq" if op==0x90 else "bne"} F_{target:04x}']
  elif op==0x4c:s += ['    rts /* explicit handoff replaces NES sprite-update JMP */']
  else:raise ValueError(op)
 s+=['translated_falling_end:']
 return '\n'.join(s)+'\n'

def sprites(chr,prg):
 # Locate the actual ROM's twelve 8x8 character OAM template records.
 pat=bytes([56,0,0,116,56,1,1,124,56,2,64,132]);assert prg.count(pat)==1
 at=prg.index(pat);records=prg[at:at+48];image=[[0]*24 for _ in range(32)]
 for k in range(12):
  yy,tile,attr,xx=records[k*4:k*4+4];cx=xx-116;cy=yy-56
  assert 0<=cx<=16 and 0<=cy<=24
  for y in range(8):
   for x in range(8):
    shift=x if attr&64 else 7-x
    image[cy+y][cx+x]=((chr[tile*16+y]>>shift)&1)|(((chr[tile*16+8+y]>>shift)&1)<<1)
 lines=['/* Converted from actual MIT-licensed Falling CHR/OAM data. */']
 for pose in ['right','left']:
  pixels=image if pose=='right' else [row[::-1] for row in image]
  for half in [0,1]:
   lines += [f'sprite_{pose}_{half}:','    .word 0,0']
   for row in pixels:
    padded=row+[0]*8; vals=[sum(((padded[half*16+x]>>plane)&1)<<(15-x) for x in range(16)) for plane in [0,1]]
    lines += [f'    .word 0x{vals[0]:04x},0x{vals[1]:04x}']
   lines += ['    .long 0']
 return '\n'.join(lines)+'\n',at+0x8000

def prepare():
 OUT.mkdir(exist_ok=True,parents=True);E.mkdir(exist_ok=True,parents=True)
 sy,prg,chr,entry,end,ins=load();visited=set();total=0
 for x in range(256):
  for d in range(53):
   for b in range(4):
    for sub in [0,64,128,255]:
     ini=[b,d,x,88,sub,1,7,8,9,33]
     got,covered=reference(ini,sy,prg,entry,ins);assert got[:9]==oracle(ini,prg),(ini,got,oracle(ini,prg))
     visited|=covered;total+=1
 cases=[]
 for b in range(4):
  for d in [0,11,12,27,28,52]:
   for x in [0,13,14,128,245,246,255]:cases.append([b,d,x,88,(x*7+d*3)&255,1,7,8,9,33])
 for y in [0,39,40,160,161,255]:
  for b in range(4):cases.append([b,0,128,y,255,1,7,8,9,33])
 # If approved Mesen reference exists, include its observed ROM states verbatim.
 trace=E/'mesen-traces.json';mesen_cases=0
 if trace.exists():
  for row in json.loads(trace.read_text()):
   mem=bytes.fromhex(row['before']);ini=[mem[sy[k]] for k in FIELDS]+[row['x0']]
   got,_=reference(ini,sy,prg,entry,ins);after=bytes.fromhex(row['after'])
   assert got[:9]==[after[sy[k]] for k in FIELDS]
   ps=row['ps1'];assert got[9:]==[row['a1'],ps&1,(ps>>1)&1,(ps>>7)&1,(ps>>6)&1,row['x1']]
   cases.append(ini);mesen_cases+=1
 rows=bytearray();expected=bytearray()
 for ini in cases:
  got,covered=reference(ini,sy,prg,entry,ins);visited|=covered
  assert got[:9]==oracle(ini,prg)
  rows.extend(ini+got);expected.extend(got)
 (OUT/'fixtures.bin').write_bytes(rows);(OUT/'expected-output.bin').write_bytes(expected)
 (OUT/'rom-prg.bin').write_bytes(prg);(OUT/'rom-selected-code.bin').write_bytes(prg[entry-32768:end-32768])
 (OUT/'translated.s').write_text(translate(ins));sp,oam=sprites(chr,prg);(OUT/'sprites.s').write_text(sp)
 (OUT/'constants.i').write_text(f'.equ CASE_COUNT,{len(cases)}\n'+''.join(f'.equ {k.upper()},{sy[k]}\n' for k in FIELDS))
 fields=['input','difficulty','x','y','subpixel_x','facing','obstacle_flag_1','obstacle_flag_2','obstacle_flag_3','A','C','Z','N','V','X']
 report={'project':'Small Mig','game':'Falling v1.1','repository':'https://github.com/xram64/falling-nes','commit':REV,'rom_sha256':ROM_SHA,'license':'MIT Copyright (c) 2018 tragicmuffin',
 'rom_bytes':40976,'mapper':0,'prg_bytes':32768,'chr_bytes':8192,'entry':hex(entry),'end_exclusive':hex(end),'native_handoff_original_jmp_target':'0xc7ed','rom_instruction_bytes':end-entry,'rom_instruction_count':len(ins),'supported_opcode_encodings':sorted(hex(x) for x in {op for p,op,a in ins}),'host_model_vs_math_cases':total,'host_instruction_addresses_exercised':len(visited),'target_fixture_count':len(cases),'mesen_reference_cases':mesen_cases,'output_bytes_per_case':15,'output_fields':fields,'oam_template_cpu_address':hex(oam)}
 (OUT/'fixture-metadata.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
 return report
if __name__=='__main__':prepare()
