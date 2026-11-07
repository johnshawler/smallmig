"""Decode native FS-UAE telemetry captures without Pillow."""
import json,sys
from png_simple import read_png
FIELDS=['magic','tick','frames','vbl','underruns','chunks_played','disp_conv','disp_skip','idle_e','audio_e','disp_e','late','maxlag','pairs','pal','apu_dropped','input','sticky_input']
def decode(path,profile=False):
 w,h,rgb=read_png(path)
 def pixel(x,y):return rgb[(y*w+x)*3:(y*w+x)*3+3]
 for scale in [2,1,3,4]:
  for y in range(h-6*scale):
   for x in range(w-256*scale):
    colors=[pixel(x+i*scale,y) for i in range(8)]
    if not(colors[0]==colors[2]==colors[3]==colors[6]==colors[7] and colors[1]==colors[4]==colors[5] and colors[0]!=colors[1]):continue
    one=colors[1]
    def word(x0,y0):
     v=0
     for i in range(32):v=(v<<1)|(pixel(x0+i*scale,y0)==one)
     return v
    magic=word(x,y)
    if magic!=(0x4c4c4230 if profile else 0x4c4c4231):continue
    vals=[word(x+(i%8)*32*scale,y+(i//8)*2*scale) for i in range(104 if profile else 18)]
    return ({'words':vals} if profile else dict(zip(FIELDS,vals)))|{'origin':[x,y],'scale':scale}
 raise ValueError('Telemetry magic not found')
if __name__=='__main__':
 for p in sys.argv[1:]:print(json.dumps({'file':p,**decode(p)}))
