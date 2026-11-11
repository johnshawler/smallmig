#!/usr/bin/env python3
"""Run additional native scripts using fresh payload copies and verified host data.

No renderer/runtime source changes. Private binaries, checkpoints and logs stay in
fresh build directories. A failed script stops at its first native mismatch;
independent scripts continue so the report shows the scope of any discrepancy.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--payload', required=True, type=Path)
    p.add_argument('--host-report', required=True, type=Path)
    p.add_argument('--musashi', required=True, type=Path)
    p.add_argument('--frames', type=int, default=6000)
    p.add_argument('--workers', type=int, choices=(1, 2, 3), default=2)
    p.add_argument('--scripts', nargs='+', choices=[f'cov{i}' for i in range(1, 9)], default=[f'cov{i}' for i in range(1, 9)])
    p.add_argument('--output', type=Path, default=ROOT/'build/little-league-native-script-matrix')
    a = p.parse_args()
    require(a.frames >= 2 and len(a.scripts) == len(set(a.scripts)), 'Invalid frames or duplicate scripts')
    host_report = a.host_report.resolve()
    host = json.loads(host_report.read_text())
    require(host['status'] == 'passed' and host['frames_per_script'] == a.frames, 'Need a passed host matrix for the exact frame count')
    require(host['fetch_bits'] == 16, 'This runner qualifies the current 16-bit compact payload only')
    payload = a.payload.resolve()
    binary = payload.with_suffix('.bin')
    source_hashes = {'elf': digest(payload), 'bin': digest(binary)}
    inputs = {}
    for script in a.scripts:
        rows = [r for r in host['results'] if r['script'] == script]
        require({r['variant'] for r in rows} == {'legacy', 'compact', 'forcedrebuild'} and len(rows) == 3,
                f'{script}: host matrix lacks the three variants')
        require(all(r['streams'] == rows[0]['streams'] for r in rows), f'{script}: host matrix streams disagree')
        row = next(r for r in rows if r['variant'] == 'compact')
        states = host_report.parent/(script+'-compact.states')
        pcm = host_report.parent/(script+'-compact.pcm')
        controller = HERE/'vendor/tools/discovery/inputs'/(script+'.txt')
        require(digest(states) == row['streams']['state']['sha256'], f'{script}: host state hash changed')
        require(digest(pcm) == row['streams']['pcm']['sha256'], f'{script}: host PCM hash changed')
        require(digest(controller) == row['input_sha256'], f'{script}: controller script changed')
        require(states.stat().st_size == a.frames*4392, f'{script}: host state count changed')
        inputs[script] = (states, pcm, controller, row)
    a.output.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%SZ-'), dir=a.output.resolve()))
    report = {'status': 'running', 'frames_per_script': a.frames, 'scripts': a.scripts,
              'payload_sha256': source_hashes, 'host_report': str(host_report),
              'host_report_sha256': digest(host_report), 'workers': a.workers, 'results': [],
              'scope': 'Native 68020 state and full PCM-hash checks, not native framebuffer or Amiga timing validation'}
    path = run/'result.json'
    print('Output: '+str(run), flush=True)

    def execute(script):
        states, pcm, controller, row = inputs[script]
        # native_check names outputs by payload parent, so give each immutable
        # copy a fresh unique parent even across repeated matrix invocations.
        copydir = run/(run.name+'-'+script)
        copydir.mkdir()
        copied = copydir/'llb.elf'
        shutil.copyfile(payload, copied)
        shutil.copyfile(binary, copied.with_suffix('.bin'))
        native_out = ROOT/'build/little-league-original/native-check'/(copydir.name+'-'+str(a.frames))
        require(not native_out.exists(), f'Refusing to overwrite {native_out}')
        command = [sys.executable, str(HERE/'native_check.py'), '--payload', str(copied),
                   '--states', str(states), '--pcm', str(pcm), '--script', str(controller),
                   '--musashi', str(a.musashi.resolve()), '--frames', str(a.frames), '--state-output']
        log = run/(script+'.log')
        result = {'script': script, 'command': command, 'native_output': str(native_out),
                  'input_sha256': row['input_sha256'], 'host_streams': row['streams']}
        try:
            with log.open('w') as stream:
                process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=2400)
            result['exit_code'] = process.returncode
            require(process.returncode == 0, f'{script}: native runner exited {process.returncode}; see {log}')
            data = json.loads((native_out/'result.json').read_text())
            require(data['native_frames'] == a.frames and data['checkpoints'] == a.frames and
                    data.get('state_mismatches', 0) == 0 and data.get('pcm_reference_hash_matched'),
                    f'{script}: incomplete state/PCM validation')
            native_states = native_out/'native-states.bin'
            require(native_states.read_bytes() == states.read_bytes(), f'{script}: native state stream differs')
            require(digest(copied) == source_hashes['elf'] and digest(copied.with_suffix('.bin')) == source_hashes['bin'],
                    f'{script}: copied payload changed')
            result.update(status='passed', native=data, native_state_sha256=digest(native_states))
            print(f'{script}: {a.frames} native checkpoints and exact PCM hash passed', flush=True)
        except Exception as error:
            result.update(status='failed', error=str(error))
            if log.exists():
                result['first_diagnostic_lines'] = [l for l in log.read_text(errors='replace').splitlines()
                                                   if 'mismatch' in l.lower() or 'offset ' in l][:12]
            print(f'{script}: FAILED: {error}; independent scripts continue', flush=True)
        if log.exists():
            result['log_sha256'] = digest(log)
        return result

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        jobs = {pool.submit(execute, script): script for script in a.scripts}
        for future in as_completed(jobs):
            try:
                report['results'].append(future.result())
            except Exception as error:
                report['results'].append({'script': jobs[future], 'status': 'failed', 'error': str(error)})
                print(f'{jobs[future]}: FAILED setup: {error}', flush=True)
            path.write_text(json.dumps(report, indent=2)+'\n')
    require(digest(payload) == source_hashes['elf'] and digest(binary) == source_hashes['bin'], 'Original payload changed during test')
    report['results'].sort(key=lambda r: a.scripts.index(r['script']))
    passed = sum(r['status'] == 'passed' for r in report['results'])
    report.update(status='passed' if passed == len(a.scripts) else 'failed', passed_scripts=passed)
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(f'{report["status"].upper()}: {path}', flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
