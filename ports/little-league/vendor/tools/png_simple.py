"""Read RGB/RGBA PNG captures using only Python's standard library."""
import pathlib,struct,zlib

def read_png(path):
 data=pathlib.Path(path).read_bytes()
 if data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Not PNG')
 pos=8;compressed=bytearray()
 while pos<len(data):
  n=struct.unpack_from('>I',data,pos)[0];kind=data[pos+4:pos+8];chunk=data[pos+8:pos+8+n];pos+=12+n
  if kind==b'IHDR':w,h,depth,color,comp,filt,interlace=struct.unpack('>IIBBBBB',chunk)
  elif kind==b'IDAT':compressed.extend(chunk)
  elif kind==b'IEND':break
 if depth!=8 or color not in (2,6) or interlace:raise ValueError((depth,color,interlace))
 bpp=3 if color==2 else 4;stride=w*bpp;raw=zlib.decompress(compressed);rows=[];prior=bytearray(stride)
 def paeth(a,b,c):
  p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
  return a if pa<=pb and pa<=pc else b if pb<=pc else c
 for y in range(h):
  at=y*(stride+1);f=raw[at];row=bytearray(raw[at+1:at+1+stride])
  for x in range(stride):
   a=row[x-bpp] if x>=bpp else 0;b=prior[x];c=prior[x-bpp] if x>=bpp else 0
   row[x]=(row[x]+(0 if f==0 else a if f==1 else b if f==2 else (a+b)//2 if f==3 else paeth(a,b,c)))&255
  rows.append(row);prior=row
 rgb=bytes(v for row in rows for i in range(0,stride,bpp) for v in row[i:i+3])
 return w,h,rgb
