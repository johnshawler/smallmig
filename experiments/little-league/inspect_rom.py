#!/usr/bin/env python3
"""Inspect a privately supplied iNES cartridge; write a CHR contact sheet."""
import hashlib,json,pathlib,struct,sys,zlib

def png(path,w,h,rgb):
 def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b))
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+rgb[y*w*3:(y+1)*w*3] for y in range(h))))+chunk(b'IEND',b''))

def inspect(path,out):
 data=path.read_bytes();assert data[:4]==b'NES\x1a'
 h=data[:16];offset=16+(512 if h[6]&4 else 0);chrdata=data[offset+h[4]*16384:]
 report={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'mapper':(h[6]>>4)|(h[7]&240),'prg_bytes':h[4]*16384,'chr_bytes':h[5]*8192}
 out.mkdir(parents=True,exist_ok=True);(out/'rom.json').write_text(json.dumps(report,indent=2)+'\n')
 pal=[(20,28,44),(83,130,153),(211,181,132),(245,245,225)]
 for bank in range(len(chrdata)//4096):
  pixels=bytearray(128*128*3)
  for t in range(256):
   tile=chrdata[bank*4096+t*16:bank*4096+t*16+16]
   for y in range(8):
    for x in range(8):
     c=((tile[y]>>(7-x))&1)|(((tile[y+8]>>(7-x))&1)<<1);pos=(((t//16)*8+y)*128+(t%16)*8+x)*3;pixels[pos:pos+3]=bytes(pal[c])
  png(out/f'chr-{bank:02}.png',128,128,pixels)
 print(json.dumps(report,indent=2))
if __name__=='__main__':inspect(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))
