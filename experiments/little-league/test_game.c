#define HOST_TEST
#include <assert.h>
#include <stdio.h>
#include "game.c"
const u8 field[40960]={0};
static void reset(void){phase=timer=swing=swung=firewas=balls=strikes=outs=hits=runs=bases=0;bx=160;inning=1;}
static void force_pitch(int x){phase=1;duration=50;pitchx=x;timer=0;swung=firewas=0;}
int main(void){int i,j;
 reset();force_pitch(160);for(i=0;i<60;i++)update(0,0);assert(strikes==1&&phase==3);
 for(j=0;j<2;j++){force_pitch(160);for(i=0;i<60;i++)update(0,0);}assert(outs==1&&strikes==0);
 reset();bases=4;balls=3;force_pitch(145);for(i=0;i<60;i++)update(0,0);assert(bases==5&&runs==0&&balls==0);
 reset();bases=7;balls=3;force_pitch(145);for(i=0;i<60;i++)update(0,0);assert(bases==7&&runs==1);
 /* Contact occurs four simulation ticks after the button edge. */
 for(j=-6;j<=6;j++){
  reset();force_pitch(160);for(i=0;i<50+j-5;i++)update(0,0);update(1,0);for(i=0;i<4;i++)update(0,0);
  assert(hits==1&&phase==2);for(i=0;i<65;i++)update(0,0);assert(phase==3);if(j>=-2&&j<=2)assert(runs==1&&bases==0);
 }
 reset();force_pitch(160);update(1,0);for(i=0;i<60;i++)update(1,0);assert(hits==0&&strikes==1);
 reset();for(i=0;i<100;i++)update(0,2);assert(bx==174);for(i=0;i<100;i++)update(0,512);assert(bx==146);
 reset();outs=2;force_pitch(160);strikes=2;for(i=0;i<60;i++)update(0,0);assert(inning==2&&outs==0);
 /* Packed sprite shifts preserve the destination outside the alpha mask. */
 {u16 data[4]={0xf000,0,0,0},mask[1]={0xf000};int shift,plane;
  for(shift=0;shift<16;shift++){
   unsigned char *bytes=screen[0];int n;
   for(n=0;n<40960;n++)bytes[n]=0xff;
   draw=bytes;sprite(shift,0,data,mask,1,1);
   for(plane=0;plane<4;plane++){
    u16 *d=(u16 *)(draw+plane*10240);
    u16 alpha=0xf000>>shift,spill=shift?((u16)(0xf000<<(16-shift))):0;
    assert(d[0]==(u16)(plane?~alpha:0xffff));
    assert(d[1]==(u16)(plane?~spill:0xffff));
   }
  }
 }
 puts("PASS: takes, strikeouts, forced walks, 13 contact timings, home runs, held fire, movement bounds, inning reset, 16 packed sprite alignments");
 return 0;
}
