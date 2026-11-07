#!/usr/bin/env python3
"""Build the original Little League engine; keep cartridge bytes private."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROM_SHA = 'f33ee3c2cdf4cb23bb060574234fa6ebb45ac0c7dea1f910d1b86c0e42990c23'


def cartridge(path):
    path = Path(path).expanduser().resolve()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != ROM_SHA:
        raise SystemExit('Unsupported cartridge revision: ' + digest)
    return path


def build(args):
    rom = cartridge(args.rom)
    prefix = next((p for p in ('m68k-elf-', 'm68k-linux-gnu-')
                   if all(shutil.which(p+t) for t in ('gcc', 'as', 'ld', 'nm', 'objcopy'))), None)
    if not prefix:
        raise SystemExit('Install m68k GCC and binutils before building.')
    out = ROOT / 'build/little-league-original'
    out.mkdir(parents=True, exist_ok=True)
    disk = out / ('Little-League-Original-Cue.adf' if args.cue_audio else 'Little-League-Original-Exact.adf')
    env = os.environ.copy()
    env.update(PREFIX=prefix, BUILD='smallmig-cue' if args.cue_audio else 'smallmig-exact',
               EXTRA='' if args.cue_audio else '-DAUDIO_EXACT', FASTRAM='1', FAST_BASE='0x200000',
               ARENDER_HW='2', RELOCATE='1', CACHE030='0', CACHE040='0', CACHE060='0')
    # Debug flags from the caller must never silently turn a player disk into a scripted test.
    for key in ('TESTINPUT', 'SNAPSHOT', 'DISPLAY_TEST', 'AUDIO_TEST', 'ARHW_TEST', 'FBFLAG', 'STATECHECK'):
        env.pop(key, None)
    subprocess.run(['sh', 'tools/build_adf.sh', str(rom), str(disk)], cwd=HERE/'vendor', env=env, check=True)
    data = disk.read_bytes()
    if len(data) != 901120:
        raise SystemExit('Unexpected ADF size')
    relocation = json.loads((HERE/'vendor/build'/env['BUILD']/'reloc.json').read_text())
    report = {'adf': disk.name, 'adf_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
              'rom_sha256': ROM_SHA, 'target': 'A1200, 68020/68030, AGA, 2 MiB Chip + at least 4 MiB Fast',
              'runtime_fast_bytes': relocation['memory_bytes'], 'loader': 'allocates and relocates into available Fast RAM',
              'playtest_profile': 'stock CPU timing' if args.stock_timing else 'FS-UAE fast CPU, JIT disabled',
              'video_standard': args.standard,
              'audio': 'approximate Paula cues' if args.cue_audio else 'original APU event PCM mixer',
              'gameplay': 'original cartridge program, statically translated with interpreter fallback',
              'acceptance': 'original-engine fidelity checks recorded; stock-speed hardware acceptance remains open'}
    (out/'build-report.json').write_text(json.dumps(report, indent=2)+'\n')
    if args.kickstart:
        ks = Path(args.kickstart).expanduser().resolve()
        if not ks.is_file():
            raise SystemExit('Kickstart file not found')
        config = ('[fs-uae]\namiga_model = A1200\ncpu = 68EC020\nchip_memory = 2048\n'
                  'fast_memory = 4096\nslow_memory = 0\nfloppy_drive_count = 1\n'
                  'floppy_drive_speed = 0\nfloppy_drive_volume = 0\n'
                  'joystick_port_1 = keyboard\njoystick_port_0 = none\n'
                  'keyboard_key_x = action_joy_1_2nd_button\n'
                  'keyboard_key_z = action_joy_1_fire_button\n'
                  'uae_cachesize = 0\nuae_blitter_cycle_exact = true\n'
                  f'uae_cpu_speed = {"real" if args.stock_timing else "max"}\n'
                  f'uae_cpu_cycle_exact = {str(args.stock_timing).lower()}\n'
                  f'uae_cpu_memory_cycle_exact = {str(args.stock_timing).lower()}\n'
                  f'ntsc_mode = {1 if args.standard == "ntsc" else 0}\n'
                  'video_sync = off\nfullscreen = 0\nwindow_width = 768\nwindow_height = 576\n'
                  'automatic_input_grab = 1\n'
                  f'kickstart_file = {ks}\nfloppy_drive_0 = {disk}\nbase_dir = {out/"fs-uae"}\n')
        (out/'Little-League.fs-uae').write_text(config)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', required=True)
    parser.add_argument('--kickstart', help='Also write a local FS-UAE player configuration')
    parser.add_argument('--cue-audio', action='store_true', help='Diagnostic faster approximate sound mode')
    parser.add_argument('--stock-timing', action='store_true', help='Write a hardware-speed diagnostic profile instead of the fast CPU playtest profile')
    parser.add_argument('--standard', choices=('ntsc', 'pal'), default='ntsc', help='Video standard for the generated FS-UAE profile')
    build(parser.parse_args())
