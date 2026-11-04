#!/usr/bin/env python3
"""One licensed-fixture task inside a dedicated local validation container."""
import json,os,pathlib,socket,subprocess,sys,time
r=pathlib.Path(__file__).resolve().parents[1];os.chdir(r)
name=os.environ['SMALL_MIG_TEST_TASK'];marker=r/'environment/task-marker.txt';marker.write_text(name+'\n')
namespaces={key:os.readlink('/proc/self/ns/'+key) for key in ['pid','mnt','ipc','net']}
seen={key:set() for key in ['Mesen','fs-uae','Xvfb']}
p=subprocess.Popen([sys.executable,str(r/'environment/startup_check.py'),'--emulators'])
while p.poll() is None:
 for path in pathlib.Path('/proc').glob('[0-9]*/comm'):
  try:
   exe=path.read_text().strip()
   if exe in seen:seen[exe].add(int(path.parent.name))
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 time.sleep(.03)
report={'task':name,'hostname':socket.gethostname(),'namespaces':namespaces,'marker_path':str(marker),'marker_value':marker.read_text().strip(),'observed_emulator_pids':{k:sorted(v) for k,v in seen.items()},'return_code':p.returncode,'network_mode':'none','codex_cloud_task':False}
(r/'environment/isolation-task-report.json').write_text(json.dumps(report,indent=2)+'\n')
assert p.returncode==0 and all(seen.values()),report
