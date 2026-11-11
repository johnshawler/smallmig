#!/usr/bin/env python3
"""Build the original Little League engine; keep cartridge bytes private."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

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
    out = ROOT / ('build/little-league-external-storage' if args.external_renderer_storage else 'build/little-league-original')
    out.mkdir(parents=True, exist_ok=True)
    disk = out / ('Little-League-Original-Cue.adf' if args.cue_audio else 'Little-League-Original-Exact.adf')
    if args.wide_dma:
        disk = disk.with_stem(disk.stem+'-Wide')
    env = os.environ.copy()
    env.update(PREFIX=prefix, BUILD='smallmig-cue' if args.cue_audio else 'smallmig-exact',
               EXTRA='' if args.cue_audio else '-DAUDIO_EXACT', FASTRAM='1', FAST_BASE='0x200000',
               ARENDER_HW='2', RELOCATE='1', CACHE030='0', CACHE040='0', CACHE060='0')
    if args.external_renderer_storage:
        env['BUILD'] += '-external-storage'
        env['EXTRA'] += ' -DAR_NO_STATIC'
    if args.wide_dma:
        env['BUILD'] += '-wide'
        env['EXTRA'] += ' -DAR2_FETCH32'
    if args.compact_rowkey:
        env['BUILD'] += '-rowkey'
        env['EXTRA'] += ' -DAR_COMPACT_ROWKEY'
        disk=disk.with_stem(disk.stem+'-Rowkey')
    # Debug flags from the caller must never silently turn a player disk into a scripted test.
    for key in ('TESTINPUT', 'SNAPSHOT', 'DISPLAY_TEST', 'AUDIO_TEST', 'ARHW_TEST', 'FBFLAG', 'STATECHECK'):
        env.pop(key, None)
    subprocess.run(['sh', 'tools/build_adf.sh', str(rom), str(disk)], cwd=HERE/'vendor', env=env, check=True)
    data = disk.read_bytes()
    if len(data) != 901120:
        raise SystemExit('Unexpected ADF size')
    relocation = json.loads((HERE/'vendor/build'/env['BUILD']/'reloc.json').read_text())
    map_name = ('memory-map'+env['BUILD'].removeprefix('smallmig')+'.json') if args.external_renderer_storage else 'memory-map.json'
    report_name = ('build-report'+env['BUILD'].removeprefix('smallmig')+'.json') if args.external_renderer_storage else 'build-report.json'
    subprocess.run([sys.executable,str(HERE/'memory_map.py'),str(HERE/'vendor/build'/env['BUILD']/'llb.elf'),
                    '--output',str(out/map_name)],check=True)
    report = {'adf': disk.name, 'adf_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
              'rom_sha256': ROM_SHA, 'target': 'PAL A1200, stock 68EC020, AGA, 2 MiB Chip + 8 MiB Fast',
              'minimum_fast_capacity_mib':4,
              'renderer_storage':'caller-owned Chip buffer only' if args.external_renderer_storage else 'caller-owned Chip buffer plus unused static fallback','memory_map':map_name,
              'source_gameplay_hz':60.0988,'presentation':'PAL vblank' if args.standard=='pal' else 'NTSC vblank',
              'sprite_row_identity':'experimental compact exact key' if args.compact_rowkey else 'legacy exact key',
              'runtime_fast_bytes': relocation['memory_bytes'], 'loader': 'allocates and relocates into available Fast RAM',
              'playtest_profile': 'stock CPU timing' if args.stock_timing else 'FS-UAE fast CPU, JIT disabled',
              'video_standard': args.standard,
              'audio': 'approximate Paula cues' if args.cue_audio else 'original APU event PCM mixer',
              'gameplay': 'original cartridge program, statically translated with interpreter fallback',
              'renderer': 'experimental 32-bit AGA DMA' if args.wide_dma else '16-bit AGA DMA',
              'acceptance': 'original-engine fidelity checks recorded; stock-speed hardware acceptance remains open'}
    (out/report_name).write_text(json.dumps(report, indent=2)+'\n')
    if args.kickstart:
        ks = Path(args.kickstart).expanduser().resolve()
        if not ks.is_file():
            raise SystemExit('Kickstart file not found')
        config = ('[fs-uae]\namiga_model = A1200\ncpu = 68EC020\nchip_memory = 2048\n'
                  'fast_memory = 8192\nslow_memory = 0\nfloppy_drive_count = 1\n'
                  'floppy_drive_speed = 0\nfloppy_drive_volume = 0\n'
                  'joystick_port_1 = keyboard\n'
                  f'joystick_port_0 = {"keyboard" if args.two_player else "none"}\n'
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
        if args.two_player:
            config += ('keyboard_key_f = action_joy_0_fire_button\n'
                       'keyboard_key_g = action_joy_0_2nd_button\n'
                       'keyboard_key_w = action_joy_0_up\nkeyboard_key_s = action_joy_0_down\n'
                       'keyboard_key_a = action_joy_0_left\nkeyboard_key_d = action_joy_0_right\n')
        (out/'Little-League.fs-uae').write_text(config)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', required=True)
    parser.add_argument('--kickstart', help='Also write a local FS-UAE player configuration')
    parser.add_argument('--cue-audio', action='store_true', help='Diagnostic faster approximate sound mode')
    parser.add_argument('--wide-dma', action='store_true', help='Build the experimental 32-bit AGA DMA renderer')
    parser.add_argument('--compact-rowkey', action='store_true', help='Build the candidate cheaper exact sprite-row identity')
    parser.add_argument('--external-renderer-storage', action='store_true', help='Candidate: omit unused renderer fallback; stage-2b player only')
    parser.add_argument('--two-player', action='store_true', help='Map player two to WASD, F and G in the FS-UAE profile')
    timing=parser.add_mutually_exclusive_group()
    timing.add_argument('--stock-timing', dest='stock_timing',action='store_true',help='Use stock CPU timing (default)')
    timing.add_argument('--fast-cpu', dest='stock_timing',action='store_false',help='Explicit accelerated emulator playtest; not hardware-speed evidence')
    parser.set_defaults(stock_timing=True)
    parser.add_argument('--standard', choices=('ntsc', 'pal'), default='pal', help='Display standard; source game clock remains unchanged')
    build(parser.parse_args())
