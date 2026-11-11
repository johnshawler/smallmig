#!/usr/bin/env python3
"""Assemble every runtime debug-flag combination and check short fallback branches."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'ports/little-league/vendor/runtime/rt_x.s'
PREFIX = next((p for p in ('m68k-elf-', 'm68k-linux-gnu-')
               if all(shutil.which(p+t) for t in ('as', 'nm', 'objdump', 'objcopy'))), None)
if PREFIX is None:
    raise SystemExit('m68k binutils required')
records = []
with tempfile.TemporaryDirectory(prefix='llb-rt-x-branches-') as directory:
    directory = Path(directory)
    for enabled in itertools.product((False, True), repeat=3):
        flags = [n for n, value in zip(('XRT_CHECK', 'XRT_STATS', 'XRT_TRACE'), enabled) if value]
        obj = directory / ('-'.join(flags or ['plain']) + '.o')
        command = [PREFIX+'as', '-m68020', '--register-prefix-optional']
        for flag in flags:
            command += ['--defsym', flag+'=1']
        subprocess.run(command + [str(SOURCE), '-o', str(obj)], check=True)
        symbols = subprocess.check_output([PREFIX+'nm', '-n', str(obj)], text=True)
        matches = re.findall(r'^([0-9a-fA-F]+) T rt_wr_gen$', symbols, re.M)
        assert len(matches) == 1, symbols
        target = int(matches[0], 16)
        binary = obj.with_suffix('.bin')
        subprocess.run([PREFIX+'objcopy', '-O', 'binary', '-j', '.text', str(obj), str(binary)], check=True)
        data = binary.read_bytes()
        disassembly = subprocess.check_output([PREFIX+'objdump', '-dr', str(obj)], text=True)
        branches = []
        for line in disassembly.splitlines():
            match = re.match(r'\s*([0-9a-f]+):\s+([0-9a-f]{4})\s+(bcss|bmis|beqs)\s+([0-9a-f]+) <rt_wr_gen>', line)
            if not match:
                continue
            address, opcode, mnemonic, printed_target = match.groups()
            address, opcode = int(address, 16), int(opcode, 16)
            assert data[address:address+2] == opcode.to_bytes(2, 'big')
            assert opcode >> 8 == {'bcss': 0x65, 'bmis': 0x6b, 'beqs': 0x67}[mnemonic]
            displacement = int.from_bytes(data[address+1:address+2], 'big', signed=True)
            assert displacement not in (0, -1)
            assert address + 2 + displacement == target == int(printed_target, 16)
            branches.append({'address': address, 'opcode': hex(opcode), 'target': target})
        assert len(branches) == 3, disassembly
        assert not re.search(r'R_68K_PC8\s+rt_wr_gen', disassembly)
        records.append({'flags': flags, 'branches': branches})
print(json.dumps({'passed': True, 'configurations': len(records), 'checked_short_branches': 3*len(records),
                  'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  'assembler': subprocess.check_output([PREFIX+'as', '--version'], text=True).splitlines()[0],
                  'records': records,
                  'scope': 'Assembly encoding/export validation, not Amiga execution or speed.'}, indent=2))
