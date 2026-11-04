#!/usr/bin/env python3
"""Fast local readiness check; --emulators runs the licensed end-to-end fixture."""
import argparse,hashlib,importlib.util,json,os,pathlib,platform,shutil,subprocess,sys
r=pathlib.Path(__file__).resolve().parents[1];os.chdir(r)
p=argparse.ArgumentParser();p.add_argument('--emulators',action='store_true');args=p.parse_args()
missing=[x for x in ['dpkg-deb','ffmpeg','import','xdpyinfo'] if shutil.which(x) is None]
if importlib.util.find_spec('PIL') is None:missing.append('Python Pillow')
local=['usr/bin/fs-uae','usr/bin/m68k-linux-gnu-as','usr/bin/Xvfb','usr/bin/xdotool','mesen-2.1.1/Mesen']
missing += [str(r/'.tools'/x) for x in local if not (r/'.tools'/x).exists()]
if missing:raise SystemExit('Missing dependencies: '+', '.join(missing))
subprocess.run([sys.executable,str(r/'build.py')],check=True,stdout=subprocess.DEVNULL)
rom=r/'experiments/homebrew/references/falling/falling.nes'
if not rom.is_file():raise SystemExit('Optional Falling fixture is not bundled. Supply the pinned local fixture described in experiments/homebrew/README.md.')
assert hashlib.sha256(rom.read_bytes()).hexdigest()=='e22b947542c2d7e595bf84725b333be7af8189c5965b9c53e356a249c7d79943'
firmware=pathlib.Path(os.environ.get('AMIGA_KICKSTART',str(r/'build/kickstart.rom')))
report={'project':'Small Mig','host_arch':platform.machine(),'tool_files_and_python_dependencies_ready':True,'native_build_passed':True,'licensed_game_fixture_hash_passed':True,'private_kickstart_available':firmware.is_file(),'actual_emulators_ran_this_check':False,'published_codex_environment':False}
if args.emulators:
 if not firmware.is_file():raise SystemExit('Supply a private A1200 Kickstart using AMIGA_KICKSTART before emulator validation.')
 target=r/'build/kickstart.rom'
 if firmware.resolve()!=target.resolve():shutil.copyfile(firmware,target)
 subprocess.run([sys.executable,str(r/'experiments/homebrew/run_test.py'),'--with-mesen'],check=True)
 report['actual_emulators_ran_this_check']=True
 report['mesen']=json.loads((r/'evidence/homebrew/mesen-report.json').read_text())
 report['fs_uae']=json.loads((r/'evidence/homebrew/positive-report.json').read_text())
(r/'environment/startup-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
