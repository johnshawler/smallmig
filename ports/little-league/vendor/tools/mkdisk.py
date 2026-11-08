#!/usr/bin/env python3
"""mkdisk.py out.adf boot.bin payload.bin
Patch the payload length into the bootblock (marker 'LLBA' at offset 16, length at offset 20, rounded up to 512), then build the ADF with mkadf.py
(bootblock checksum + payload at ADF byte 1024)."""
import json, os, struct, subprocess, sys, tempfile
here = os.path.dirname(os.path.abspath(__file__))
mkadf = os.path.join(here, 'mkadf.py')
out, boot, payload = sys.argv[1:4]
bb = bytearray(open(boot, 'rb').read())
pl = open(payload, 'rb').read()
assert bb[16:20] == b'LLBA', 'bootblock marker missing'
n = (len(pl) + 511) & ~511
assert n <= 880*1024 - 1024, 'payload does not fit on the disk'
struct.pack_into('>I', bb, 20, n)
if bb[24:28] == b'RLOC':
    assert len(sys.argv) == 5, 'relocatable bootblock needs its relocation metadata'
    meta = json.load(open(sys.argv[4]))
    assert meta['memory_bytes'] >= n
    assert meta['reloc_offset'] + 4*meta['reloc_count'] <= len(pl)
    struct.pack_into('>4I', bb, 28, meta['memory_bytes'], meta['base'], meta['reloc_offset'], meta['reloc_count'])
with tempfile.NamedTemporaryFile(delete=False) as f:
    f.write(bb); tmp = f.name
try:
    subprocess.check_call([sys.executable, mkadf, out, tmp, payload])
finally:
    os.unlink(tmp)
print('%s: bootblock %d bytes, payload %d bytes (read %d)' % (out, len(bb), len(pl), n))
