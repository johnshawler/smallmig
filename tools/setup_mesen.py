#!/usr/bin/env python3
"""Stage a pinned official Mesen release. Does not execute the emulator."""
import hashlib,json,pathlib,platform,urllib.request,zipfile
r=pathlib.Path(__file__).resolve().parents[1]
assert platform.machine()=='x86_64'
p=r/'.tools/downloads/Mesen_2.1.1_Linux_x64.zip';p.parent.mkdir(parents=True,exist_ok=True)
url='https://github.com/SourMesen/Mesen2/releases/download/2.1.1/Mesen_2.1.1_Linux_x64.zip'
if not p.exists():urllib.request.urlretrieve(url,p)
assert hashlib.sha256(p.read_bytes()).hexdigest()=='7a9947575cc198209f743fef83fb2b702b786ea705506bdf3f2aea01ab7c1ce9'
dest=r/'.tools/mesen-2.1.1';dest.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(p) as z:
 assert z.namelist()==['Mesen']
 (dest/'Mesen').write_bytes(z.read('Mesen'))
(dest/'Mesen').chmod(0o755)
if not (dest/'settings.json').exists():(dest/'settings.json').write_text('{}\n')
print('Official Mesen 2.1.1 staged locally; no system-wide install or execution.')
