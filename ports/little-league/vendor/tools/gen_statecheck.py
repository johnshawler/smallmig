#!/usr/bin/env python3
"""Turn private rt_host STATEOUT records into native RAM-check constants."""
from pathlib import Path
import struct
import sys

data = Path(sys.argv[1]).read_bytes()
size = 8+2048+256+32+2048
if not data or len(data) % size or len(data)//size>31:
    raise SystemExit('Invalid STATEOUT record size')
previous = -1
for i in range(0, len(data), size):
    frame = struct.unpack_from('<Q', data, i)[0]
    if not previous < frame < 0x7FFFFFFF:
        raise SystemExit('STATEOUT frames must be increasing 32-bit values')
    previous = frame
    value = 2166136261
    for b in data[i+8:i+2056]:
        value = ((value ^ b)*16777619) & 0xFFFFFFFF
    print('{ %du, 0x%08Xu },' % (frame, value))
