#!/usr/bin/env python3
"""Compare an FS-UAE full screenshot with one original-engine RGB frame, without Pillow."""
import argparse
import json
from pathlib import Path
import struct
from png_simple import read_png
from gen_palette import table


def compare(shot, reference, frame, std='pal', ignore=0):
    data = Path(reference).read_bytes()
    size = 8+240*256*2
    if len(data) % size:
        raise ValueError('Truncated framebuffer file')
    ref = next((data[i+8:i+size] for i in range(0,len(data),size)
                if struct.unpack_from('<Q',data,i)[0]==frame), None)
    if ref is None:
        raise ValueError('Reference frame not present')
    w,h,rgb = read_png(shot)
    ox,oy = 138,52 if std=='pal' else 0
    if not 0<=ignore<240 or w<ox+512 or h<oy+480:
        raise ValueError('Invalid crop or screenshot size')
    palette = table(); differences=0; nonuniform=0; first=[]
    for y in range(240-ignore):
        for x in range(256):
            value=struct.unpack_from('<H',ref,2*(y*256+x))[0]
            expected=palette[value&255].to_bytes(3,'big')
            index=((oy+y*2)*w+ox+x*2)*3
            actual=rgb[index:index+3]
            if actual!=expected:
                differences+=1
                if len(first)<8: first.append({'x':x,'y':y,'expected':expected.hex(),'actual':actual.hex()})
            if any(rgb[index+off:index+off+3]!=actual for off in (3,w*3,w*3+3)):
                nonuniform+=1
    return {'frame':frame,'pixels_compared':(240-ignore)*256,'differences':differences,
            'nonuniform_blocks':nonuniform,'ignored_bottom_lines':ignore,'first':first}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('shot');p.add_argument('reference');p.add_argument('frame',type=int)
    p.add_argument('--standard',choices=['pal','ntsc'],default='pal')
    p.add_argument('--ignore-lines',type=int,default=0)
    a=p.parse_args();r=compare(a.shot,a.reference,a.frame,a.standard,a.ignore_lines)
    print(json.dumps(r,indent=2));raise SystemExit(bool(r['differences'] or r['nonuniform_blocks']))
