#!/usr/bin/env python3
"""Pinned local tool preparation; optional Debian-13 runtime package installation."""
import argparse,importlib,os,pathlib,platform,subprocess,sys
r=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--install-runtime',action='store_true');args=p.parse_args()
assert platform.machine()=='x86_64','Pinned host packages are Linux x86_64 only'
if args.install_runtime:
 release=pathlib.Path('/etc/os-release').read_text()
 if 'VERSION_ID="13"' not in release or 'ID=debian' not in release:raise SystemExit('Runtime lock supports Debian 13; do not install it into another distro.')
 if os.geteuid()!=0:raise SystemExit('Runtime installation needs the environment setup runner to be root; no system changes attempted.')
 packages=[x for x in (r/'environment/runtime-debian13.lock').read_text().splitlines() if x]
 subprocess.run(['apt-get','update'],check=True)
 subprocess.run(['apt-get','install','-y','--no-install-recommends',*packages],check=True)
for script in ['tools/setup.py','tools/setup_mesen.py']:
 subprocess.run([sys.executable,str(r/script)],check=True)
subprocess.run([sys.executable,str(r/'environment/startup_check.py')],check=True)
print('Local tool setup complete. This does not create or publish a Codex environment.')
