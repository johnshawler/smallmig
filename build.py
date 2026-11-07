#!/usr/bin/env python3
"""One-command build: ELF for inspection, raw bootblock, checksummed ADF."""
import os, pathlib, struct, subprocess, hashlib, json, shutil
root = pathlib.Path(__file__).resolve().parent
os.chdir(root)
out = root / 'build'
out.mkdir(exist_ok=True)
tools = root / '.tools/usr'
env = dict(os.environ, LD_LIBRARY_PATH=str(tools / 'lib/x86_64-linux-gnu'))
def run(name, *args):
    result = subprocess.run([(shutil.which('m68k-elf-' + name) or str(tools / ('bin/m68k-linux-gnu-' + name))), *args], env=env, capture_output=True)
    if result.returncode:
        raise SystemExit(result.stderr.decode(errors='replace'))
    return result
run('as', '-m68020', '--register-prefix-optional', '-o', 'build/boot.o', 'src/boot.s')
run('ld', '-Ttext=0', '-e', '_start', '-o', 'build/boot.elf', 'build/boot.o')
run('objcopy', '-O', 'binary', 'build/boot.elf', 'build/boot.raw')
raw = (out/'boot.raw').read_bytes()
assert 12 < len(raw) <= 1024, f'Boot payload too large: {len(raw)}'
block = bytearray(raw.ljust(1024, b'\0'))
s = 0
for (word,) in struct.iter_unpack('>I', block):
    s += word
    s = (s & 0xffffffff) + (s >> 32)
struct.pack_into('>I', block, 4, (~s) & 0xffffffff)
check = 0
for (word,) in struct.iter_unpack('>I', block):
    check += word
    check = (check & 0xffffffff) + (check >> 32)
assert check == 0xffffffff
adf = block + bytes(901120 - len(block))
(out/'harness.adf').write_bytes(adf)
(out/'boot.disassembly.txt').write_bytes(run('objdump','-d','build/boot.elf').stdout)
report = {'payload_bytes': len(raw), 'adf_bytes': len(adf), 'explicit_chip_allocation_bytes': 16384, 'explicit_fast_allocation_bytes': 0, 'adf_sha256': hashlib.sha256(adf).hexdigest(), 'boot_checksum': hex(check), 'runtime_minimum_measured': False}
(out/'build-report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))

