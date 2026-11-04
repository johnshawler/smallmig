#!/usr/bin/env python3
"""Restore pinned Debian x86_64 host tools locally, without root or apt changes."""
import hashlib, json, pathlib, platform, subprocess, urllib.request
root = pathlib.Path(__file__).resolve().parents[1]
assert platform.machine() == 'x86_64', 'These host packages are x86_64 only'
folder = root/'.tools'
(folder/'downloads').mkdir(parents=True, exist_ok=True)
for pkg in json.loads((root/'tools/host-packages.json').read_text()):
    dest = folder/'downloads'/(pkg['name']+'.deb')
    if not dest.exists():
        print('Downloading', pkg['name'], flush=True)
        urllib.request.urlretrieve(pkg['url'], dest)
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == pkg['sha256'], dest
    subprocess.run(['dpkg-deb','-x',str(dest),str(folder)],check=True)
print('Host tools ready in .tools/. Runtime shared libraries must exist on the host.')
