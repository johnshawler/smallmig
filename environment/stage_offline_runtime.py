#!/usr/bin/env python3
"""Stage already-installed public runtime files for offline local isolation tests.
No network access or environment publication. Records exact file hashes.
"""
import glob,hashlib,json,os,pathlib,re,shutil,subprocess
r=pathlib.Path(__file__).resolve().parents[1];context=r/'environment/docker-context';root=context/'rootfs'
root.mkdir(exist_ok=True);copied=set()
def copy(src):
 src=pathlib.Path(src)
 if not src.exists() or str(src).startswith('/workspace/'):return
 canonical=src.parent.resolve()/src.name
 if str(canonical) in copied:return
 copied.add(str(canonical));dst=root/str(canonical).lstrip('/');dst.parent.mkdir(parents=True,exist_ok=True)
 if src.is_symlink():
  target=os.readlink(src)
  if dst.is_symlink() or dst.exists():dst.unlink()
  dst.symlink_to(target)
  copy(pathlib.Path(target) if target.startswith('/') else src.parent/target)
 else:shutil.copy2(src,dst)
def deps(path):
 result=subprocess.run(['ldd',str(path)],capture_output=True,text=True,env=dict(os.environ,LD_LIBRARY_PATH=str(r/'.tools/usr/lib/x86_64-linux-gnu')))
 for name in re.findall(r'(?:=>\s*)?(/[^\s()]+)',result.stdout):copy(name)
programs=['/usr/bin/python3','/usr/bin/import','/usr/bin/ffmpeg','/usr/bin/xdpyinfo','/usr/bin/xkbcomp','/usr/bin/dpkg-deb']
for path in programs:copy(path);deps(path)
directories=['/usr/lib/python3.13','/usr/lib/python3/dist-packages/PIL','/usr/lib/x86_64-linux-gnu/ImageMagick-7.1.1','/usr/share/ImageMagick-7','/etc/ImageMagick-7','/usr/share/X11','/usr/share/glvnd','/usr/lib/locale/C.utf8']
for path in directories:
 p=pathlib.Path(path)
 if p.exists():
  for f in p.rglob('*'):
   if f.is_file() and '__pycache__' not in f.parts:copy(f)
libs=['libGL.so.1','libGLX.so.0','libGLdispatch.so.0','libGLX_mesa.so.0','libEGL.so.1','libEGL_mesa.so.0','libstdc++.so.6','libicuuc.so.76','libicui18n.so.76','libicudata.so.76','libicuio.so.76','libicutu.so.76']
for name in libs:
 p=pathlib.Path('/usr/lib/x86_64-linux-gnu')/name
 if p.exists():copy(p);deps(p)
for p in pathlib.Path('/usr/lib/x86_64-linux-gnu/dri').glob('*.so'):copy(p);deps(p)
for path in [root/'usr/lib/python3.13',root/'usr/lib/python3/dist-packages/PIL',root/'usr/lib/x86_64-linux-gnu/ImageMagick-7.1.1']:
 for p in path.rglob('*.so'):
  if p.is_file():deps(pathlib.Path('/')/p.relative_to(root))
for path in ['usr/bin/fs-uae','usr/bin/Xvfb','usr/bin/xdotool','usr/bin/m68k-linux-gnu-as','usr/bin/m68k-linux-gnu-ld','usr/bin/m68k-linux-gnu-objcopy']:
 deps(r/'.tools'/path)
app=context/'source';target=app/'.tools';target.mkdir(exist_ok=True)
if (target/'usr').exists():shutil.rmtree(target/'usr')
shutil.copytree(r/'.tools/usr',target/'usr',symlinks=True)
(target/'mesen-2.1.1').mkdir(exist_ok=True)
shutil.copy2(r/'.tools/mesen-2.1.1/Mesen',target/'mesen-2.1.1/Mesen')
(target/'mesen-2.1.1/settings.json').write_text('{}\n')
manifest=[]
for f in root.rglob('*'):
 if f.is_symlink():manifest.append({'path':'/'+str(f.relative_to(root)),'symlink':os.readlink(f)})
 elif f.is_file():manifest.append({'path':'/'+str(f.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(r/'environment/offline-runtime-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Staged',len(manifest),'existing runtime files/links without network access.')
