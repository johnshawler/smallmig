#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Rebuild and execute both controls; leave the positive disk as the default."""
import json, pathlib, subprocess, sys
here=pathlib.Path(__file__).resolve().parent
for name, options in [('probe.py',[]),('verify_target.py',[]),('probe.py',['--negative']),('verify_target.py',['--negative']),('probe.py',[])]:
    subprocess.run([sys.executable,str(here/name),*options],check=True)
r=here.parents[1]
positive=json.loads((r/'evidence/probe/positive-report.json').read_text())
negative=json.loads((r/'evidence/probe/negative-report.json').read_text())
assert positive['actual_bytes_match_uncorrupted_reference'] and negative['actual_bytes_match_uncorrupted_reference']
assert not positive['target_self_check_failed'] and negative['target_self_check_failed']
print('PASS: native output matches; corrupted expected result detected; positive disk restored.')
