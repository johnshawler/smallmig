#!/usr/bin/env python3
"""Restore Debian m68k tools privately; never installs or runs package maintainer scripts.
Requires Debian 13 amd64 host runtime libraries, Python 3, curl, gpg, and dpkg-deb.
The signed package index and downloaded .deb files are cached for reproducibility.
"""
import hashlib, json, lzma, os, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROV=ROOT/'provenance'; DEBS=ROOT/'downloads'; DEST=ROOT/'root'
BASE='https://deb.debian.org/debian/'
KEYRING=Path('/usr/share/keyrings/debian-archive-keyring.gpg')
NAMES='gcc-m68k-linux-gnu cpp-m68k-linux-gnu gcc-14-m68k-linux-gnu gcc-14-m68k-linux-gnu-base cpp-14-m68k-linux-gnu gcc-14-cross-base-ports libgcc-14-dev-m68k-cross libgcc-s2-m68k-cross libgomp1-m68k-cross libatomic1-m68k-cross binutils-m68k-linux-gnu binutils-common libc6-dev-m68k-cross libc6-m68k-cross linux-libc-dev-m68k-cross qemu-user'.split()
for p in (PROV, DEBS, DEST, ROOT/'gnupg'): p.mkdir(parents=True,exist_ok=True)
def fetch(url,path):
    if not path.exists():
        subprocess.run(['curl','--fail','--location','--retry','2',url,'-o',str(path)+'.partial'],check=True)
        Path(str(path)+'.partial').rename(path)
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
fetch(BASE+'dists/trixie/InRelease',PROV/'InRelease')
gpg=subprocess.run(['gpg','--batch','--no-options','--homedir',str(ROOT/'gnupg'),'--no-default-keyring','--keyring',str(KEYRING),'--status-fd','1','--verify',str(PROV/'InRelease')],capture_output=True,text=True)
(PROV/'InRelease-verification.txt').write_text(gpg.stdout+gpg.stderr)
if gpg.returncode or '[GNUPG:] VALIDSIG ' not in gpg.stdout:
    raise SystemExit('Official Debian keyring signature verification failed; inspect provenance/InRelease-verification.txt')
release=(PROV/'InRelease').read_text()
if '\nCodename: trixie\n' not in release: raise SystemExit('Unexpected Debian codename')
sha=release.split('SHA256:\n',1)[1].split('\nSHA512:',1)[0]
m=re.search(r'^ ([0-9a-f]{64})\s+(\d+)\s+main/binary-amd64/Packages.xz$',sha,re.M)
if not m: raise SystemExit('Signed SHA256 package index entry not found')
fetch(BASE+'dists/trixie/main/binary-amd64/by-hash/SHA256/'+m[1],PROV/'Packages.xz')
if (PROV/'Packages.xz').stat().st_size!=int(m[2]) or digest(PROV/'Packages.xz')!=m[1]: raise SystemExit('Package index SHA256 mismatch')
packages={}
for block in lzma.decompress((PROV/'Packages.xz').read_bytes()).decode().split('\n\n'):
    d={}
    for line in block.splitlines():
        if ': ' in line and not line.startswith(' '):
            k,v=line.split(': ',1); d[k]=v
    if 'Package' in d: packages[d['Package']]=d
lock=[]
for name in NAMES:
    p=packages[name]
    lock.append({k:p[k] for k in ('Package','Version','Architecture','Filename','Size','SHA256')})
lockpath=PROV/'packages-lock.json'
if lockpath.exists() and json.loads(lockpath.read_text())!=lock: raise SystemExit('Refusing changed package lock; use a new recovery directory for updates')
lockpath.write_text(json.dumps(lock,indent=2)+'\n')
for p in lock:
    target=DEBS/Path(p['Filename']).name
    fetch(BASE+p['Filename'],target)
    if target.stat().st_size!=int(p['Size']) or digest(target)!=p['SHA256']: raise SystemExit('Package SHA256 mismatch: '+p['Package'])
    print('Verified and extracting',p['Package'],p['Version'],flush=True)
    subprocess.run(['dpkg-deb','--extract',str(target),str(DEST)],check=True)
(PROV/'SHA256SUMS').write_text(''.join(f'{p["SHA256"]}  downloads/{Path(p["Filename"]).name}\n' for p in lock))
(PROV/'source.json').write_text(json.dumps({'repository':BASE,'distribution':'trixie','architecture':'amd64','release_sha256':digest(PROV/'InRelease'),'packages_xz_sha256':digest(PROV/'Packages.xz'),'host_keyring':str(KEYRING),'host_keyring_sha256':digest(KEYRING),'verification':'gpg verified InRelease using the preinstalled Debian archive keyring; InRelease SHA256 verifies Packages.xz; package SHA256 verifies each .deb; no package maintainer scripts executed.','host_runtime_dependency':'Debian 13 amd64 native runtime shared libraries remain supplied by the host. This is a private cross toolchain, not a chroot or replacement host runtime.'},indent=2)+'\n')
print('Restore completed:',DEST)
