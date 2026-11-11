#!/usr/bin/env python3
"""Budget-entry liveness regressions, with optional actual 68020 execution.

Run with MUSASHI_DIR and an m68k compiler on PATH for independent native tests.
Without those dependencies the analysis/codegen tests still run; native tests
are explicitly skipped. All fixtures are synthetic and require no cartridge.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'vendor/translator'))
import x65


def program(chunks):
    prg = bytearray(131072)
    seen = []
    for address, code in chunks:
        prg[address-0x8000:address-0x8000+len(code)] = bytes(code)
        offset = 0
        while offset < len(code):
            seen.append((0, address+offset))
            offset += x65.LEN[x65.T[code[offset]][1]]
    prog = x65.Prog(x65.Rom(prg), seen)
    blocks = x65.build_blocks(prog)
    live = x65.liveness(prog, blocks)
    return prog, blocks, live


def generate(chunks):
    prog, blocks, live = program(chunks)
    g = x65.Gen(prog, blocks, live, set(blocks))
    for key in sorted(blocks):
        g.gen_block(blocks[key])
    return '\n'.join(g.out), prog, blocks, live


# Successor kills every tracked flag, but may escape before any instruction.
KILL = [0x18, 0xa9, 0, 0xb8, 0x60]  # CLC; LDA #0; CLV; RTS


class EntryLiveness(unittest.TestCase):
    def test_jump_preserves_flags_before_successor_kills(self):
        asm, prog, blocks, live = generate([(0x8000,[0xc9,1,0x4c,8,0x80]),(0x8008,KILL)])
        self.assertTrue(all(v == x65.ALL for v in live.values()))
        self.assertEqual(prog.ins[(0,0x8000)].live, x65.ALL)
        first = asm.split('B0_8008:')[0]
        self.assertIn('scc d4', first)
        self.assertIn('move.b (a5,d7.w),(0,a2)', first)
        self.assertIn('jmp rt_slow', first)

    def test_branch_target_cannot_fuse_away_flags(self):
        asm, prog, blocks, live = generate([(0x8000,[0xc9,1,0xb0,4,*KILL[:-1]]),(0x8008,KILL)])
        g = x65.Gen(prog, blocks, live, set(blocks))
        g.b = blocks[(0,0x8000)]
        self.assertEqual(g.live_taken(prog.ins[(0,0x8002)]),x65.ALL)
        self.assertIn('scc d4',asm.split('B0_8008:')[0])

    def test_fallthrough_query_includes_guard(self):
        prog, blocks, live = program([(0x8000,[0xc9,1]),(0x8002,KILL),
                                     (0x8010,[0x4c,2,0x80])])
        g = x65.Gen(prog,blocks,live,set(blocks)); g.b=blocks[(0,0x8000)]
        self.assertEqual(g.b.fall,(0,0x8002))
        self.assertEqual(g.live_fall_after(len(g.b.ins)),x65.ALL)
        self.assertEqual(prog.ins[(0,0x8000)].live,x65.ALL)

    def test_intrablock_dead_flags_still_eliminated(self):
        asm, prog, blocks, live = generate([(0x8000,[0xc9,1,*KILL])])
        self.assertEqual(prog.ins[(0,0x8000)].live & (x65.C|x65.N|x65.Z),0)
        self.assertNotIn('scc d4',asm)


class NativeBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        musashi=os.environ.get('MUSASHI_DIR')
        cls.prefix=next((p for p in ('m68k-elf-','m68k-linux-gnu-') if shutil.which(p+'gcc')),None)
        if not musashi or not cls.prefix:
            raise unittest.SkipTest('Set MUSASHI_DIR and put m68k tools on PATH for native execution')
        musashi=Path(musashi).resolve()
        cls.temp=tempfile.TemporaryDirectory(prefix='interrupt-flags-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.out=Path(cls.temp.name)
        cc=shutil.which('clang') or shutil.which('cc')
        subprocess.run([cc,'-O2',str(musashi/'m68kmake.c'),'-o',str(cls.out/'make')],check=True)
        subprocess.run([str(cls.out/'make'),str(cls.out),str(musashi/'m68k_in.c')],check=True,stdout=subprocess.DEVNULL)
        subprocess.run([cc,'-O2','-I'+str(cls.out),'-I'+str(musashi),str(HERE/'interrupt_flags_cpu.c'),
                        str(musashi/'m68kcpu.c'),str(cls.out/'m68kops.c'),str(musashi/'softfloat/softfloat.c'),
                        '-lm','-o',str(cls.out/'cpu')],check=True)

    def run_boundary(self,chunks,a,old_p,operand,expected,boundary=0x8008,budget=None):
        asm, prog, blocks, live = generate(chunks)
        asm='.text\n.globl B0_8000\n'+asm+'\nrt_slow:\n bra rt_slow\nrt_disp:\n bra rt_disp\n'
        (self.out/'code.s').write_text(asm)
        subprocess.run([self.prefix+'as','-m68020','--register-prefix-optional',str(self.out/'code.s'),'-o',str(self.out/'code.o')],check=True)
        subprocess.run([self.prefix+'ld','-Ttext=0x1000','-e','B0_8000',str(self.out/'code.o'),'-o',str(self.out/'code.elf')],check=True)
        subprocess.run([self.prefix+'objcopy','-O','binary',str(self.out/'code.elf'),str(self.out/'code.bin')],check=True)
        syms=subprocess.check_output([self.prefix+'nm',str(self.out/'code.elf')],text=True)
        stop=next(int(l.split()[0],16) for l in syms.splitlines() if l.split()[-1]=='rt_slow')
        if budget is None: budget=sum(i.cyc for i in blocks[(0,0x8000)].ins)
        result=subprocess.check_output([str(self.out/'cpu'),str(self.out/'code.bin'),str(stop),str(budget),
                                        str(a),str(old_p),str(operand),str(boundary)],text=True)
        self.assertEqual(int(result.split()[0]),expected)

    def test_cmp_carry_both_directions_and_nz(self):
        for a,old,expected in [(2,0x24,0x25),(0,0x25,0xa4),(1,0xa4,0x27)]:
            with self.subTest(a=a,old=old):
                self.run_boundary([(0x8000,[0xc9,1,0x4c,8,0x80]),(0x8008,KILL)],a,old,0,expected)

    def test_bit_nzv_both_directions(self):
        for a,old,operand,expected in [(0,0x24,0xc0,0xe6),(255,0xe6,1,0x24)]:
            with self.subTest(old=old,operand=operand):
                self.run_boundary([(0x8000,[0x24,0,0x4c,8,0x80]),(0x8008,KILL)],a,old,operand,expected)

    def test_taken_branch_materializes_carry(self):
        self.run_boundary([(0x8000,[0xc9,1,0xb0,4,*KILL[:-1]]),(0x8008,KILL)],2,0x24,0,0x25)

    def test_fallthrough_materializes_flags(self):
        self.run_boundary([(0x8000,[0xc9,1]),(0x8002,KILL),(0x8010,[0x4c,2,0x80])],
                          0,0x25,0,0xa4,boundary=0x8002)


if __name__ == '__main__':
    unittest.main()
