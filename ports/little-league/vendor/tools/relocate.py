#!/usr/bin/env python3
"""Extract a checked 680x0 relocation table from a linked ELF32 big-endian image.

Offsets with bit 31 clear add the load delta; bit 31 set subtracts it for
PC-relative references to fixed Chip RAM. Cartridge bytes are never inspected.
"""
import argparse
import json
from pathlib import Path
import struct


def entries(path, base, load_size):
    data = Path(path).read_bytes()
    if data[:6] != b'\x7fELF\x01\x02':
        raise ValueError('Expected big-endian ELF32')
    if struct.unpack_from('>H', data, 18)[0] != 4:
        raise ValueError('Expected m68k ELF')
    shoff = struct.unpack_from('>I', data, 32)[0]
    shsize, count = struct.unpack_from('>HH', data, 46)
    if shsize != 40:
        raise ValueError('Unsupported section header size')
    sections = [struct.unpack_from('>10I', data, shoff+i*40) for i in range(count)]

    def symbols(index):
        sec = sections[index]
        return [struct.unpack_from('>IIIBBH', data, i)
                for i in range(sec[4], sec[4]+sec[5], sec[9])]

    def fast(symbol):
        index = symbol[5]
        return 0 < index < count and sections[index][2] & 2 and sections[index][3] >= base

    result = set()
    seen_relocations = 0
    for sec in sections:
        if sec[1] != 4:  # SHT_RELA
            if sec[1] == 9:
                raise ValueError('SHT_REL is not supported; use GNU m68k ELF RELA')
            continue
        source = sections[sec[7]]
        if not source[2] & 2 or source[1] == 8 or source[3] < base:
            continue
        sym = symbols(sec[6])
        if sec[9] != 12:
            raise ValueError('Unexpected RELA entry size')
        for pos in range(sec[4], sec[4]+sec[5], 12):
            address, info, addend = struct.unpack_from('>IIi', data, pos)
            kind, target = info & 255, sym[info >> 8]
            offset = address-base
            if kind == 0:
                continue
            seen_relocations += 1
            moving_target = fast(target)
            if kind == 1 and moving_target:  # R_68K_32
                entry = offset
            elif kind == 4 and not moving_target:  # R_68K_PC32 to fixed memory
                entry = offset | 0x80000000
            elif (kind in (4, 5, 6) and moving_target) or (kind in (1, 2, 3) and not moving_target):
                continue
            else:
                raise ValueError(f'Unsupported cross-region relocation type {kind} at {address:#x}')
            if offset < 0 or offset+4 > load_size or offset & 1:
                raise ValueError('Relocation outside load image or not word aligned')
            result.add(entry)
    if not seen_relocations or not result:
        raise ValueError('No relocations: link with --emit-relocs')
    return sorted(result)


def apply(image, relocations, delta):
    data = bytearray(image)
    for entry in relocations:
        offset = entry & 0x7FFFFFFF
        value = struct.unpack_from('>I', data, offset)[0]
        value += -delta if entry & 0x80000000 else delta
        struct.pack_into('>I', data, offset, value & 0xFFFFFFFF)
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf'); p.add_argument('payload'); p.add_argument('metadata')
    p.add_argument('--base', type=lambda x: int(x, 0), required=True)
    p.add_argument('--memory-bytes', type=lambda x: int(x, 0), required=True)
    args = p.parse_args()
    payload = Path(args.payload)
    image = payload.read_bytes()
    relocations = entries(args.elf, args.base, len(image))
    table = b''.join(struct.pack('>I', entry) for entry in relocations)
    if len(image) & 3:
        raise SystemExit('Load image must be longword aligned')
    metadata = {'base': args.base, 'memory_bytes': max(args.memory_bytes, len(image)+len(table)),
                'reloc_offset': len(image), 'reloc_count': len(relocations)}
    payload.write_bytes(image+table)
    Path(args.metadata).write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
