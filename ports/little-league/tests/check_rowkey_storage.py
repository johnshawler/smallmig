#!/usr/bin/env python3
"""Qualify guarded legacy, compact and forced-rebuild row keys against the dot PPU.

Outputs are private: states and PCM contain cartridge-derived data. Each invocation
creates a fresh run directory, preserving previous evidence even when a run fails.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from build import cartridge, ROOT

VARIANTS = {
    'legacy': [],
    'compact': ['-DAR_COMPACT_ROWKEY'],
    'forcedrebuild': ['-DAR_COMPACT_ROWKEY', '-DAR_NOROWCACHE'],
}
FLAGS = ['-O2', '-DPPU_FB5', '-DRT_AUDIO=1', '-DAR_NO_STATIC']
SCRIPTS = ['play_watchgame', *[f'cov{i}' for i in range(1, 9)]]
RUNTIME = ['rt_core', 'cpu6502', 'ppu_ref', 'arender', 'mapper_mmc1', 'apu']
STATE_BYTES = 4392


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_streams(prefix, frames):
    states = prefix.with_suffix('.states').read_bytes()
    require(len(states) == frames * STATE_BYTES, f'{prefix}: state record size/count')
    for n in range(frames):
        require(int.from_bytes(states[n * STATE_BYTES:n * STATE_BYTES + 8], 'little') == n,
                f'{prefix}: state frame index {n}')
    pcm = prefix.with_suffix('.pcm').read_bytes()
    # Match audio_words.h's exact PAL period-124 rational cadence, not an average.
    num, den = 5 * (11803 * 39375000 + 21423809), 248 * 39375000
    offset = samples = 0
    for n in range(frames):
        require(offset + 2 <= len(pcm), f'{prefix}: missing PCM header {n}')
        words = int.from_bytes(pcm[offset:offset + 2], 'big')
        expected = ((n + 1) * num // den) - (n * num // den)
        require(words == expected, f'{prefix}: PAL PCM words at frame {n}: {words} != {expected}')
        offset += 2 + 2 * words
        samples += 2 * words
        require(offset <= len(pcm), f'{prefix}: truncated PCM record {n}')
    require(offset == len(pcm), f'{prefix}: extra PCM bytes')
    return {
        'state': {'sha256': hashlib.sha256(states).hexdigest(), 'bytes': len(states),
                  'records': frames, 'record_bytes': STATE_BYTES},
        'pcm': {'sha256': hashlib.sha256(pcm).hexdigest(), 'bytes': len(pcm),
                'records': frames, 'samples': samples, 'format': 'u16be word count + signed 8-bit samples'},
    }


def validate_log(prefix, frames):
    log = prefix.with_suffix('.log').read_text()
    require('FAIL' not in log, f'{prefix}: failure marker')
    require(log.count('STORAGE: both layer sets observed, guards intact') == 1,
            f'{prefix}: missing or repeated guard/layer marker')
    patterns = {
        'ppu_comparisons': r'^PPU_CHECK: (\d+) comparisons passed, (\d+) exotic situations$',
        'planar_frames': r'^ARENDER: (\d+) frames identical to the reference, (\d+) exact \(chunky\) rows in total$',
        'frames': r'^done: (\d+) frames, (\d+) cycles$',
    }
    values = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, log, re.MULTILINE)
        require(len(matches) == 1, f'{prefix}: missing/repeated {key} comparison marker')
        values[key] = int(matches[0][0])
        values[{'ppu_comparisons': 'exotic_situations', 'planar_frames': 'exact_rows', 'frames': 'cycles'}[key]] = int(matches[0][1])
    require(values['ppu_comparisons'] > 0, f'{prefix}: no per-dot comparisons')
    # Host startup begins before ar_begin_frame; only subsequent frames have a scene.
    require(values['frames'] == frames and values['planar_frames'] == frames - 1,
            f'{prefix}: incomplete frame/oracle coverage: {values}')
    values.update(guard_checks='passed', layer_selections=[0, 1], log_sha256=digest(prefix.with_suffix('.log')))
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', required=True)
    parser.add_argument('--frames', type=int, default=6000)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/little-league-corrected-rowkey/host-tests')
    args = parser.parse_args()
    if args.frames < 2:
        parser.error('frames must be at least two')
    rom = cartridge(args.rom)
    cc = shutil.which('clang') or shutil.which('cc')
    require(cc is not None, 'No host C compiler found')
    args.output.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%SZ-'), dir=args.output.resolve()))
    # Allowlist avoids inherited debug/output knobs, loader injections and compiler flags.
    env = {key: os.environ[key] for key in ('PATH', 'HOME', 'TMPDIR', 'SYSTEMROOT') if key in os.environ}
    env.update(LC_ALL='C', PPU_CHECK='1', ARENDER='2', RT_LAZY='1', DRAWPAT='1', PCMSTD='pal')
    sources = [HERE / 'tests/external_storage_runner.c', *[HERE / 'vendor/runtime' / f'{r}.c' for r in RUNTIME]]
    report = {'status': 'running', 'frames_per_script': args.frames, 'scripts': SCRIPTS,
              'fetch_bits': 16, 'audio': 'exact host PAL', 'rom_sha256': digest(rom),
              'compiler': subprocess.check_output([cc, '--version'], env=env, text=True),
              'environment': {k: env[k] for k in ('LC_ALL', 'PPU_CHECK', 'ARENDER', 'RT_LAZY', 'DRAWPAT', 'PCMSTD')},
              'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in sources},
              'builds': {}, 'results': []}
    report_path = out / 'result.json'
    print(f'Output: {out}', flush=True)
    try:
        for variant, extra in VARIANTS.items():
            command = [cc, *FLAGS, *extra, '-o', str(out / variant), *map(str, sources)]
            with (out / f'{variant}-build.log').open('w') as log:
                subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            report['builds'][variant] = {'command': command, 'flags': FLAGS + extra, 'sha256': digest(out / variant)}

        def run(job):
            script, variant = job
            prefix = out / f'{script}-{variant}'
            script_path = HERE / 'vendor/tools/discovery/inputs' / f'{script}.txt'
            runenv = dict(env, STATEOUT=str(prefix.with_suffix('.states')), PCMOUT=str(prefix.with_suffix('.pcm')))
            with prefix.with_suffix('.log').open('w') as log:
                subprocess.run([str(out / variant), str(rom), str(args.frames), str(script_path)],
                               env=runenv, stdout=log, stderr=subprocess.STDOUT, check=True)
            result = {'script': script, 'variant': variant, 'input_sha256': digest(script_path),
                      'checks': validate_log(prefix, args.frames), 'streams': validate_streams(prefix, args.frames)}
            print(f'{script}/{variant}: per-dot, planar, guards, both layers and records passed', flush=True)
            return result

        with ThreadPoolExecutor(max_workers=3) as pool:
            for result in pool.map(run, [(s, v) for s in SCRIPTS for v in VARIANTS]):
                report['results'].append(result)
                report_path.write_text(json.dumps(report, indent=2) + '\n')
        for script in SCRIPTS:
            rows = [r for r in report['results'] if r['script'] == script]
            require(len(rows) == 3 and all(r['streams'] == rows[0]['streams'] for r in rows),
                    f'{script}: legacy/compact/forcedrebuild state or PCM mismatch')
            print(f'{script}: all three state and PCM streams identical', flush=True)
        report.update(status='passed', total_runs=len(report['results']), total_frames=args.frames * len(report['results']))
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS: {report_path}', flush=True)


if __name__ == '__main__':
    main()
