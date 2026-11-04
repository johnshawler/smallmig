#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Build and test the native slice. Does not execute unfamiliar third-party tools."""
import pathlib,subprocess,sys
here=pathlib.Path(__file__).resolve().parent
names=['build.py','verify_native.py']
if '--with-mesen' in sys.argv:names.insert(0,'run_mesen_reference.py')
for name in names:
 subprocess.run([sys.executable,str(here/name)],check=True)
