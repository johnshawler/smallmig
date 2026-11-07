#!/usr/bin/env python3
"""Independent original-fixture pixel oracle, including NES first-eight rules."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import gen_palette


def pattern(bank,tile,y,x):
    return ((x+3*y+tile+bank)&3) if tile else 0


def picture(frame):
    yy,xx=np.indices((240,256))
    fine=frame%8; bx=xx+fine
    tilex=bx//8; tiley=yy//8
    addr=(tilex//32)*1024+tiley*32+(tilex&31)
    tile=addr%15+1
    bank=(frame>>3)&1; large=(frame>>4)&1
    p=(bx%8+3*(yy%8)+tile+bank)&3
    shift=((tiley&2)<<1)|(tilex&2)
    pal=(0xe4>>shift)&3
    bg=(pal*4+p).astype(np.uint8)
    bg[(p==0)|(xx<8)]=0
    result=bg.copy()
    height=16 if large else 8
    for y in range(1,240):
        # Select before looking at tile transparency or horizontal clipping.
        selected=[i for i in range(64) if (i//9)*28+8<=y-1<(i//9)*28+8+height][:8]
        claimed=np.zeros(256,dtype=bool)
        for i in selected:
            sy=(i//9)*28+8;ti=i%16
            at=(i&3)|(0x20 if i&1 else 0)|(0x40 if i&2 else 0)|(0x80 if i&4 else 0)
            sx=(i%9)*27+(frame//2)%7
            row=y-1-sy
            if at&0x80:row=height-1-row
            if large:
                address=((0x1000 if ti&1 else 0)|((ti&~1)<<4))+(row+8 if row>=8 else row)
            else:address=(ti<<4)+row
            graphics_bank=bank if address<0x1000 else bank^1
            tile=(address&4095)//16;row=address&7
            for px in range(8):
                x=sx+px
                if x>=256 or x<8 or claimed[x]:continue
                sc=pattern(graphics_bank,tile,row,7-px if at&0x40 else px)
                if not sc:continue
                claimed[x]=True
                if not (at&0x20 and (bg[y,x]&3)):
                    result[y,x]=16+(at&3)*4+sc
    return result


def main():
    shot,observed=sys.argv[1:3]
    h=2166136261
    for frame in range(64):
        final=picture(frame)
        for b in final.tobytes():h=((h^b)*16777619)&0xffffffff
    if h!=int(observed):
        raise SystemExit(f'All-frame index mismatch: expected {h:08x}, got {int(observed):08x}')
    colours=np.array(gen_palette.table(),dtype=np.uint32)
    rgb=colours[(final.astype(np.uint32)*7+3)&63]
    image=np.asarray(Image.open(shot).convert('RGB')).astype(np.uint32)
    im=image[52:532:2,138:650:2]
    got=(im[:,:,0]<<16)|(im[:,:,1]<<8)|im[:,:,2]
    bad=rgb!=got
    print(f'{shot}: {int(bad.sum())} pixels differ; all 64 native frame hashes match')
    if bad.any():
        print('First differing coordinates:',np.argwhere(bad)[:16].tolist())
        raise SystemExit(1)


if __name__=='__main__':
    main()
