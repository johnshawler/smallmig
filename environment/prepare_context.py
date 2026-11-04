#!/usr/bin/env python3
"""Prepare a source-only local image context; private firmware is excluded."""
import pathlib,shutil
r=pathlib.Path(__file__).resolve().parents[1];context=r/'environment/docker-context';app=context/'source'
app.mkdir(parents=True,exist_ok=True)
for name in ['build.py','run.py','README.md']:
 shutil.copy2(r/name,app/name)
shutil.copytree(r/'src',app/'src',dirs_exist_ok=True)
for name in ['tools','environment']:
 dest=app/name;dest.mkdir(exist_ok=True)
 for p in (r/name).iterdir():
  if p.is_file():shutil.copy2(p,dest/p.name)
for folder in ['6502-probe','homebrew']:
 dest=app/'experiments'/folder;dest.mkdir(parents=True,exist_ok=True)
 for p in (r/'experiments'/folder).iterdir():
  if p.is_file():shutil.copy2(p,dest/p.name)
upstream=app/'experiments/homebrew/references/falling';(upstream/'source').mkdir(parents=True,exist_ok=True)
for name in ['falling.nes','LICENSE','README.md','source/falling.asm','source/falling.chr']:
 shutil.copy2(r/'experiments/homebrew/references/falling'/name,upstream/name)
shutil.copy2(r/'environment/Dockerfile',context/'Dockerfile')
print(context)
