#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Run the pinned official NES reference separately from native Amiga output."""
import hashlib,json,os,pathlib,subprocess,sys
import falling
r=falling.ROOT
binary=r/'.tools/mesen-2.1.1/Mesen'
if not binary.exists():raise SystemExit('Restore official Mesen first: python3 tools/setup_mesen.py')
shared_runtime=pathlib.Path('/usr/lib/x86_64-linux-gnu/libstdc++.so.6')
if not shared_runtime.exists():raise SystemExit('This verified runtime workaround expects Debian x86_64 libstdc++.so.6')
env=dict(os.environ,LD_PRELOAD=str(shared_runtime),DOTNET_BUNDLE_EXTRACT_BASE_DIR=str(binary.parent/'bundle'))
args=[str(binary),'--testRunner','--enableStdout','--timeout=15','--nes.port1.type=NesController',str(falling.HERE/'mesen-reference.lua'),str(falling.UP/'falling.nes')]
falling.E.mkdir(parents=True,exist_ok=True)
result=subprocess.run(args,env=env,capture_output=True,timeout=25)
log=falling.E/'mesen-reference-runtime.log';log.write_bytes(result.stdout+result.stderr)
if result.returncode:raise SystemExit(f'Mesen exited {result.returncode}; see {log}')
subprocess.run([sys.executable,str(falling.HERE/'parse_mesen_log.py'),str(log)],check=True)
report=json.loads((falling.E/'mesen-report.json').read_text())
report.update({'official_zip_sha256':'7a9947575cc198209f743fef83fb2b702b786ea705506bdf3f2aea01ab7c1ce9','return_code':result.returncode,'runtime_workaround':'Preload existing host libstdc++.so.6 to avoid std::bad_cast from bundled C++ locale facet','lua_io_os_network_enabled':False,'explicit_controller':'NesController on port 1','command':args})
(falling.E/'mesen-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
