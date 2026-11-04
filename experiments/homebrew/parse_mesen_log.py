#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Parse an approved Mesen run's stdout. Does not launch Mesen."""
import json,pathlib,sys
import falling
source=pathlib.Path(sys.argv[1]);rows=[];completed=None
for line in source.read_text(errors='replace').splitlines():
 for prefix in ['SMALL_MIG_TRACE ','SMALL_MIG_COMPLETE ']:
  if prefix in line:
   obj=json.loads(line.split(prefix,1)[1])
   if prefix.endswith('TRACE '):rows.append(obj)
   else:completed=obj
assert completed and rows and completed['movement_calls']==len(rows)
assert all(r['x0']>=0 and r['a1']>=0 and r['ps1']>=0 for r in rows), 'Mesen state field mismatch'
sy,prg,chr,entry,end,ins=falling.load()
for row in rows:
 before=bytes.fromhex(row['before']);after=bytes.fromhex(row['after'])
 ini=[before[sy[k]] for k in falling.FIELDS]+[row['x0']]
 got,_=falling.reference(ini,sy,prg,entry,ins)
 assert got[:9]==[after[sy[k]] for k in falling.FIELDS],row['frame']
 ps=row['ps1'];assert got[9:]==[row['a1'],ps&1,(ps>>1)&1,(ps>>7)&1,(ps>>6)&1,row['x1']],row['frame']
(falling.E/'mesen-traces.json').write_text(json.dumps(rows,indent=2)+'\n')
(falling.E/'mesen-report.json').write_text(json.dumps({'verified':True,'emulator':'Mesen 2.1.1','rom_sha256':falling.ROM_SHA,'frames':completed['frames'],'observed_movement_calls':len(rows),'selected_memory_and_flags_match_model':True,'full_game_completion_tested':False},indent=2)+'\n')
print('Mesen reference matched',len(rows),'observed ROM movement calls. Rebuild native fixtures to include them.')
