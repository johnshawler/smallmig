#!/usr/bin/env python3
"""Check the original 64-state sprite fixture's PUAE log and final capture.

Reuses the existing independent first-eight/pixel oracle. The historical FS-UAE
checker and its crop are unchanged. This checker expects PUAE's 720x287 capture
with a doubled-horizontal 512x240 game area at (104, 26).
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'vendor/tests/amiga'))
import ar_sprite_expect as oracle

np = oracle.np
Image = oracle.Image
CROP = (104, 26, 512, 240)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def diagnostics(text):
    def word(reg):
        values = re.findall(r'00d0%04x=([0-9a-fA-F]{8})' % reg, text, re.IGNORECASE)
        require(len(values) == 1, f'Missing or repeated diagnostic word at {0xd00000 + reg:#x}')
        # UAE logs may sign-extend a 16-bit write to a 32-bit hex argument.
        return int(values[0], 16) & 0xffff

    def value(reg):
        return (word(reg) << 16) | word(reg + 2)

    require(word(0) == 0x534d and word(2) == 5, 'Sprite fixture did not complete with 0x534d / 5')
    result = {
        'renderer_eclock_ticks': value(0x10),
        'max_renderer_eclock_ticks': value(0x14),
        'observed_fnv32': value(0x18),
        'cache': {name: value(0x20 + 4 * i) for i, name in enumerate(('calls', 'hits', 'misses', 'oam_words'))},
        'percentiles': {name: value(0x30 + 4 * i) for i, name in enumerate(('p50', 'p95', 'p99'))},
    }
    cache = result['cache']
    require(cache['calls'] == 64 * 240, 'Incomplete 64-state scanline coverage')
    require(cache['hits'] + cache['misses'] == cache['calls'], 'Inconsistent cache counters')
    pct = result['percentiles']
    require(0 < pct['p50'] <= pct['p95'] <= pct['p99'] == result['max_renderer_eclock_ticks'],
            'Invalid timing percentiles')
    require(result['renderer_eclock_ticks'] >= result['max_renderer_eclock_ticks'], 'Invalid aggregate timing')
    return result


def expected():
    h = 2166136261
    for frame in range(64):
        final, layer = oracle.picture(frame)
        for k in range(4):
            for b in np.packbits((layer >> k) & 1, axis=1, bitorder='big').tobytes():
                h = ((h ^ b) * 16777619) & 0xffffffff
    colours = np.array(oracle.gen_palette.table(), dtype=np.uint32)
    rgb = colours[(final.astype(np.uint32) * 7 + 3) & 63]
    return h, np.repeat(rgb, 2, axis=1)


def check_pixels(image, rgb):
    x, y, width, height = CROP
    crop = image[y:y + height, x:x + width]
    require(crop.shape == (height, width, 3), 'Capture is too small for the exact PUAE crop')
    got = (crop[:, :, 0] << 16) | (crop[:, :, 1] << 8) | crop[:, :, 2]
    bad = got != rgb
    require(not bad.any(), f'{int(bad.sum())} final display pixels differ (both horizontal copies checked)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--variant', required=True, choices=('legacy', 'compact', 'rebuild'))
    parser.add_argument('--output', type=Path, help='Optional JSON report; raw captures remain unchanged')
    args = parser.parse_args()
    result = diagnostics(args.log.read_text())
    h, rgb = expected()
    require(result['observed_fnv32'] == h, f'64-state sprite-plane hash mismatch: expected {h}, got {result["observed_fnv32"]}')
    image = np.asarray(Image.open(args.image).convert('RGB')).astype(np.uint32)
    check_pixels(image, rgb)
    result.update(variant=args.variant, pictures=64, expected_fnv32=h, crop=list(CROP),
                  mismatched_display_pixels=0, completed=True,
                  log_sha256=hashlib.sha256(args.log.read_bytes()).hexdigest(),
                  image_sha256=hashlib.sha256(args.image.read_bytes()).hexdigest(),
                  scope='PUAE synthetic sprite/Copper fixture, not full-game speed or physical Amiga validation')
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
