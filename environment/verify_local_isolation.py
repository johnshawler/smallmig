#!/usr/bin/env python3
"""Run two separate, network-disabled local containers. Not Codex Cloud tasks."""
import json,os,pathlib,subprocess,time,uuid
r=pathlib.Path(__file__).resolve().parents[1];dest=r/'environment/isolation';dest.mkdir(exist_ok=True)
env=dict(os.environ,DOCKER_CONFIG=str(r/'environment/docker-config'))
def docker(*args):return subprocess.check_output(['docker',*args],env=env,text=True).strip()
image=docker('image','inspect','small-mig-base:verified','--format','{{.Id}}')
created=[];processes=[];reports=[]
try:
 for task in ['A','B']:
  name='small-mig-isolation-'+uuid.uuid4().hex[:8]+'-'+task.lower()
  cid=docker('create','--network','none','--name',name,'--env','SMALL_MIG_TEST_TASK='+task,'small-mig-base:verified','python3','environment/isolation_task.py')
  created.append((task,cid))
  # Copy private user-provided firmware into each disposable writable layer.
  docker('cp',str(r/'build/kickstart.rom'),cid+':/app/SmallMig/build/kickstart.rom')
 for task,cid in created:
  log=open(dest/('task-'+task+'.log'),'w')
  p=subprocess.Popen(['docker','start','-a',cid],env=env,stdout=log,stderr=log)
  processes.append((task,cid,p,log))
 deadline=time.monotonic()+160
 while any(p.poll() is None for task,cid,p,log in processes):
  if time.monotonic()>deadline:raise RuntimeError('Local isolation test timeout')
  time.sleep(.2)
 for task,cid,p,log in processes:
  log.close()
  docker('cp',cid+':/app/SmallMig/environment/isolation-task-report.json',str(dest/('task-'+task+'-report.json')))
  docker('cp',cid+':/app/SmallMig/environment/startup-report.json',str(dest/('task-'+task+'-startup.json')))
  report=json.loads((dest/('task-'+task+'-report.json')).read_text());reports.append(report)
  assert p.returncode==0 and report['return_code']==0,(task,p.returncode,report)
 assert reports[0]['marker_value']=='A' and reports[1]['marker_value']=='B'
 for namespace in ['pid','mnt','ipc','net']:
  assert reports[0]['namespaces'][namespace]!=reports[1]['namespaces'][namespace],namespace
 summary={'image_id':image,'local_containers_only':True,'published_codex_environment':False,'codex_environment_id':None,'two_actual_codex_cloud_tasks_tested':False,'both_licensed_emulator_tests_passed':True,'same_in_container_paths_independent_marker_values':True,'separate_pid_mount_ipc_network_namespaces':True,'network_disabled':True,'tasks':reports}
 (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
finally:
 for task,cid in created:
  subprocess.run(['docker','rm','-f',cid],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
