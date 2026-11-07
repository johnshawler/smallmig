"""Reconstruct the game's batting view from Mesen's mapped PPU/OAM snapshot."""
from collections import Counter,defaultdict
import json,pathlib,struct
from inspect_rom import png
OUT=pathlib.Path(__file__).resolve().parents[2]/'build/little-league';S=OUT/'source'

def extract():
 ppu=(S/'PPU-2400.bin').read_bytes();oam=(S/'OAM-2400.bin').read_bytes();rgb=(S/'RGB-2400.bin').read_bytes()
 def bgpixel(x,y):
  tile=ppu[0x2000+(y//8)*32+x//8];att=ppu[0x23c0+(y//32)*8+x//32];pal=(att>>(((y//16)%2)*4+((x//16)%2)*2))&3
  lo=ppu[4096+tile*16+y%8];hi=ppu[4096+tile*16+8+y%8];c=((lo>>(7-x%8))&1)|(((hi>>(7-x%8))&1)<<1)
  return ppu[0x3f00+(pal*4+c if c else 0)]&63
 background=[bgpixel(x,y) for y in range(240) for x in range(256)]
 counts=defaultdict(Counter)
 for i,c in enumerate(background):counts[c][tuple(rgb[i*3:i*3+3])]+=1
 colors={c:v.most_common(1)[0][0] for c,v in counts.items()}
 # Source palette entries absent from the background are learned from the same
 # frame's actual sprite pixels, using the OAM's palette and flip bits.
 layers={}
 for stamp in [2400,3300]:
  p=(S/f'PPU-{stamp}.bin').read_bytes();o=(S/f'OAM-{stamp}.bin').read_bytes();actual=(S/f'RGB-{stamp}.bin').read_bytes();spr=[-1]*(256*240)
  for i in range(252,-1,-4):
   yy,t,a,xx=o[i:i+4]
   for y in range(8):
    sy=7-y if a&128 else y
    for x in range(8):
     sx=7-x if a&64 else x;c=((p[t*16+sy]>>(7-sx))&1)|(((p[t*16+sy+8]>>(7-sx))&1)<<1)
     if c and xx+x<256 and yy+1+y<240:spr[(yy+1+y)*256+xx+x]=p[0x3f10+(a&3)*4+c]&63
  for idx,c in enumerate(spr):
   if c>=0:counts[c][tuple(actual[idx*3:idx*3+3])]+=1
  layers[stamp]=spr
 colors={c:v.most_common(1)[0][0] for c,v in counts.items()}
 # Four bitplanes permit 16 colours. The captured source uses fewer than 16.
 unique=list(dict.fromkeys(colors.values()));assert len(unique)<=16,unique
 palette=[((r>>4)<<8)|((g>>4)<<4)|(b>>4) for r,g,b in unique];palette += [0]*(16-len(palette))
 mapped={c:unique.index(v) for c,v in colors.items()}
 def crop(stamp,x,y,w,h):return [mapped[layers[stamp][yy*256+xx]] if layers[stamp][yy*256+xx]>=0 else 255 for yy in range(y,y+h) for xx in range(x,x+w)]
 poses=[crop(2400,108,24,32,40),crop(3300,108,24,32,40),crop(2400,136,144,40,72)]
 im=bytearray(320*256)
 for y in range(240):
  for x in range(256):im[(y+8)*320+x+32]=mapped[background[y*256+x]]
 # Bake the native HUD backdrops once; avoid repainting 16,320 pixels per tick.
 ink=min(range(len(unique)),key=lambda i:sum(v*v for v in unique[i]))
 for y in list(range(27))+list(range(232,256)):
  im[y*320:(y+1)*320]=bytes([ink])*320
 planar=bytearray(40960)
 for p in range(4):
  for y in range(256):
   for x in range(320):
    if im[y*320+x]&(1<<p):planar[p*10240+y*40+x//8]|=128>>(x&7)
 (OUT/'field.bin').write_bytes(planar)
 header='static const unsigned short palette[16]={'+','.join(hex(x) for x in palette)+'};\n'
 for n,data,w,h in [('pitcher_idle',poses[0],32,40),('pitcher_throw',poses[1],32,40),('batter',poses[2],40,72)]:
  words=(w+15)//16
  mask=[];planes=[[] for _ in range(4)]
  for y in range(h):
   for word in range(words):
    m=0;pv=[0,0,0,0]
    for bit in range(16):
     x=word*16+bit;c=data[y*w+x] if x<w else 255
     if c!=255:
      m|=0x8000>>bit
      for plane in range(4):
       if c&(1<<plane):pv[plane]|=0x8000>>bit
    mask.append(m)
    for plane in range(4):planes[plane].append(pv[plane])
  for suffix,values in [('_mask',mask),('',sum(planes,[]))]:
   header+='static const unsigned short '+n+suffix+'[]={'+','.join(map(str,values))+'};\n'

 # Fixed native colors, chosen from the captured game's palette.
 def nearest(rgb):return min(range(len(unique)),key=lambda i:sum((a-b)**2 for a,b in zip(unique[i],rgb)))
 header+='enum { INK='+str(nearest((0,0,0)))+', PAPER='+str(nearest((255,255,255)))+', ACCENT='+str(nearest((255,190,60)))+' };\n'
 (OUT/'assets.h').write_text(header)
 out=bytes(v for c in im for v in ((palette[c]>>8)*17,((palette[c]>>4)&15)*17,(palette[c]&15)*17));png(OUT/'field.png',320,256,out)
 for name,data,w,h in [('pitcher',poses[0],32,40),('batter',poses[2],40,72)]:
  png(OUT/(name+'.png'),w,h,bytes(v for c in data for v in (unique[c] if c!=255 else (20,20,20))))
 predicted=[layers[2400][i] if layers[2400][i]>=0 else c for i,c in enumerate(background)]
 matched=sum(tuple(rgb[i*3:i*3+3])==colors[c] for i,c in enumerate(predicted))
 report={'source_frame':2400,'rgb_reconstruction_matches':matched,'pixels':61440,'palette_colors':len(unique),'sprite_mapping':'Actual mapped CHR plus OAM, 8x8 sprites, flip bits and per-sprite palettes','limitations':'Single batting-view capture. No translated gameplay or original audio.'};(OUT/'source-graphics-report.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':extract()
