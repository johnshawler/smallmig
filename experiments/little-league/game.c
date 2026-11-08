/* Small Mig: first native batting-loop prototype, not translated NES logic. */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
#ifdef HOST_TEST
static volatile u16 registers[256];
#define REG(n) registers[(n)/2]
#define PTR(n,p) ((void)(p))
#else
#define REG(n) (*(volatile u16 *)(0xdff000UL+(n)))
#define PTR(n,p) (*(volatile u32 *)(0xdff000UL+(n))=(u32)(p))
#endif
#include "assets.h"
extern const u8 field[];
static u8 screen[2][40960] __attribute__((aligned(4)));
static u16 copper[2][100] __attribute__((aligned(4)));
static signed char tone[128] __attribute__((aligned(4)));
static u8 *draw;
static int front, frame, phase, timer, bx=160, ballx,bally, pitchx, duration;
static int swing, swung, firewas, balls,strikes,outs,hits,runs,bases,inning=1;
static int result, aim, flight, vx,vy, soundleft;
static u32 rng=0x6842;
/* 5x7 font, original simple block lettering. */
static const u8 font[36][7]={
 {14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},{30,1,1,14,1,1,30},{2,6,10,18,31,2,2},{31,16,16,30,1,1,30},{14,16,16,30,17,17,14},{31,1,2,4,8,8,8},{14,17,17,14,17,17,14},{14,17,17,15,1,1,14},
 {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{14,17,16,16,16,17,14},{30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},{14,17,16,23,17,17,15},{17,17,17,31,17,17,17},{14,4,4,4,4,4,14},{7,2,2,2,2,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},{17,27,21,21,17,17,17},{17,25,21,19,17,17,17},{14,17,17,17,17,17,14},{30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},{15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},{17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},{17,17,10,4,4,4,4},{31,1,2,4,8,16,31}};
static int length(const char *s){int n=0;while(s[n])n++;return n;}
static int absn(int n){return n<0?-n:n;}
static u32 randomn(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static void pixel(int x,int y,int c){int p,at;
 if(x<0||x>=320||y<0||y>=256)return;
 at=y*40+(x>>3);for(p=0;p<4;p++){u8 *a=draw+p*10240+at;u8 mask=128>>(x&7);
 if(c&(1<<p))*a|=mask;else *a&=~mask;}}
static void box(int x,int y,int w,int h,int c){int i,j;for(j=0;j<h;j++)for(i=0;i<w;i++)pixel(x+i,y+j,c);}
static void line(int x,int y,int xx,int yy,int c){int n=absn(xx-x),m=absn(yy-y),i;
 if(m>n)n=m;
 for(i=0;i<=n;i++)pixel(x+(xx-x)*i/(n?n:1),y+(yy-y)*i/(n?n:1),c);}
static void text(int x, int y, const char *s, int color)
{
 while(*s) {
  int k=(*s>='0'&&*s<='9')?*s-'0':(*s>='A'&&*s<='Z')?*s-'A'+10:-1;
  if(k>=0) {
   int row,plane;
   for(row=0;row<7;row++) {
    u16 bits=(u16)font[k][row]<<(11-(x&7));
    int offset=(y+row)*40+(x>>3);
    for(plane=0;plane<4;plane++) {
     u8 *d=draw+plane*10240+offset;
     if(color&(1<<plane)) {d[0]|=bits>>8;d[1]|=bits;}
     else {d[0]&=~(bits>>8);d[1]&=~bits;}
    }
   }
  }
  x+=6;s++;
 }
}
static void number(int x,int y,int n){char b[4];b[0]='0'+(n/10)%10;b[1]='0'+n%10;b[2]=0;text(x,y,b,PAPER);}
static void sprite(int x, int y, const u16 *data, const u16 *mask, int words, int h)
{
 int row,plane,j,shift=x&15;
 int span=words*h;
 /* Shift packed rows at word granularity; one mask serves all four planes. */
 for(plane=0;plane<4;plane++) for(row=0;row<h;row++) {
  u16 *dst=(u16 *)(draw+plane*10240+(y+row)*40+(x>>4)*2);
  const u16 *src=data+plane*span+row*words;
  const u16 *m=mask+row*words;
  u16 previous=0,previous_mask=0;
  for(j=0;j<=words;j++) {
   u16 v=j<words?src[j]:0;
   u16 mm=j<words?m[j]:0;
   u16 out=shift?(v>>shift)|(previous<<(16-shift)):v;
   u16 alpha=shift?(mm>>shift)|(previous_mask<<(16-shift)):mm;
   dst[j]=(dst[j]&~alpha)|out;
   previous=v;previous_mask=mm;
  }
 }
}
static void sound(int kind){int i;REG(0x96)=1;for(i=0;i<128;i++){int env=128-i;tone[i]=(signed char)((kind==1?((i*37)&127)-64:((i&8)?60:-60))*env/128);}PTR(0xa0,tone);REG(0xa4)=64;REG(0xa6)=kind==1?140:kind==2?250:380;REG(0xa8)=40;REG(0x96)=0x8201;soundleft=kind==1?5:3;}
static void finish(int r){result=r;phase=3;timer=60;sound(r>=4?1:2);}
static void score(int n){int i;for(i=0;i<n;i++){if(bases&4)runs++;bases=(bases<<1)&7;
 if(i==0)bases|=1;}}
static void out(void){outs++;balls=strikes=0;
 if(outs==3){outs=0;bases=0;inning++;}finish(3);}
static void pitch(void){timer=0;swung=0;swing=0;duration=42+(randomn()%15);pitchx=145+(randomn()%31);ballx=150;bally=62;phase=1;result=0;}
static void update(int fire,int joy){int edge=fire&&!firewas;firewas=fire;frame++;
 if(soundleft&&!--soundleft){REG(0xa8)=0;REG(0x96)=1;}if(swing)swing--;
 if(joy&2)bx++;
 if(joy&512)bx--;
 if(bx<146)bx=146;
 if(bx>174)bx=174;
 if(phase==0){if(edge||++timer>65)pitch();return;}
 if(phase==1){timer++;ballx=150+(pitchx-150)*timer/duration;bally=62+149*timer/duration;
  if(edge&&!swung){swung=1;swing=12;sound(0);aim=(joy&2)?1:(joy&512)?-1:0;}
  /* Bat passes the plate four ticks into the twelve-tick animation. */
  if(swung&&swing==8&&absn(timer-duration)<=6&&absn(pitchx-bx)<=10){int timing=timer-duration;hits++;flight=0;vx=aim*2+timing/3;vy=-2;ballx=pitchx;bally=207;phase=2;result=absn(timing)<=2?6:absn(timing)<=4?5:4;sound(1);return;}
  if(timer>=duration+8){if(swung||absn(pitchx-160)<=11){strikes++;
 if(strikes>=3){out();return;}finish(1);}else{balls++;
 if(balls>=4){balls=strikes=0;
 if(bases==7)runs++;
 bases|=(bases+1)&7;finish(7);}else finish(2);}}
 }else if(phase==2){flight++;ballx+=vx;bally+=vy;
 if(flight>42)vy=1;
 if(ballx<25)ballx=25;
 if(ballx>295)ballx=295;
 if(flight==65){score(result==6?4:result-3);balls=strikes=0;finish(result);}}
 else if(phase==3){if(--timer<=0||edge){phase=0;timer=0;}}
}
static void waitblit(void){while(REG(2)&0x4000){}}
static void background(void){
#ifdef HOST_TEST
 int i;for(i=0;i<40960;i++)draw[i]=field[i];
#else
 waitblit();REG(0x40)=0x09f0;REG(0x42)=0;REG(0x44)=0xffff;REG(0x46)=0xffff;REG(0x64)=0;REG(0x66)=0;PTR(0x50,field);PTR(0x54,draw);REG(0x58)=(640<<6)|32;waitblit();
#endif
}
static void render(void)
{
 const char *msg="FIRE TO PITCH";
 background();
 /* Reuse the source batting view; the native scoreboard identifies this slice. */

 text(9,3,"LITTLE LEAGUE    SMALL MIG BATTING",PAPER);
 text(9,16,"IN",PAPER);number(27,16,inning);
 text(51,16,"OUT",PAPER);number(75,16,outs);
 text(99,16,"B",PAPER);number(111,16,balls);
 text(135,16,"S",PAPER);number(147,16,strikes);
 text(171,16,"HITS",PAPER);number(201,16,hits);
 text(225,16,"RUNS",PAPER);number(255,16,runs);
 if(phase==1&&timer>7) sprite(140,32,pitcher_throw,pitcher_throw_mask,2,40);
 else sprite(140,32,pitcher_idle,pitcher_idle_mask,2,40);
 sprite(bx+8,152,batter,batter_mask,3,72);
 if(swing) line(bx+26,186,bx-7,201,ACCENT);
 if(phase==1||phase==2) {
  box(ballx-1,bally-1,3,3,PAPER);
  pixel(ballx,bally,INK);
 }
 if(phase==1)msg="WATCH THE BALL";
 if(phase==2)msg="IN PLAY";
 if(phase==3) {
  const char *messages[]={"READY","STRIKE","BALL","STRIKEOUT","SINGLE","DOUBLE","HOME RUN","WALK"};
  msg=messages[result];
 }
 /* Occupied bases appear over the original diamond diagram. */
 if(bases&1)box(258,133,4,4,ACCENT);
 if(bases&2)box(242,119,4,4,ACCENT);
 if(bases&4)box(226,133,4,4,ACCENT);

 text(160-3*length(msg),233,msg,PAPER);
 text(16,245,"ARROWS MOVE   SPACE OR RCTRL SWING",PAPER);
}
/* Called during the PAL vertical blank. No OS calls after takeover. */
static void display(int b){int p;for(p=0;p<4;p++){u32 ptr=(u32)(screen[b]+p*10240);copper[b][p*4]=0xe0+p*4;copper[b][p*4+1]=ptr>>16;copper[b][p*4+2]=0xe2+p*4;copper[b][p*4+3]=ptr;}copper[b][16]=0xffff;copper[b][17]=0xfffe;PTR(0x80,copper[b]);REG(0x88)=0;}
void game_main(void){REG(0x9a)=0x7fff;REG(0x96)=0x7fff;REG(0x9c)=0x7fff;REG(0x100)=0x4200;REG(0x102)=0;REG(0x104)=0;REG(0x106)=0;REG(0x108)=0;REG(0x10a)=0;REG(0x1fc)=0;REG(0x1e4)=0;REG(0x8e)=0x2c81;REG(0x90)=0x2cc1;REG(0x92)=0x38;REG(0x94)=0xd0;
/* Unroll volatile palette writes: m68k GCC 16 combines the loop with an
   unsafe postincrement of the shared source/destination address register. */
REG(0x180)=palette[0];
REG(0x182)=palette[1];
REG(0x184)=palette[2];
REG(0x186)=palette[3];
REG(0x188)=palette[4];
REG(0x18a)=palette[5];
REG(0x18c)=palette[6];
REG(0x18e)=palette[7];
REG(0x190)=palette[8];
REG(0x192)=palette[9];
REG(0x194)=palette[10];
REG(0x196)=palette[11];
REG(0x198)=palette[12];
REG(0x19a)=palette[13];
REG(0x19c)=palette[14];
REG(0x19e)=palette[15];
REG(0x96)=0x8240;draw=screen[0];render();display(0);REG(0x96)=0x83c0;
 for(;;){
 int joy=REG(0x0c);
 int fire=!(*(volatile u8*)0xbfe001&128);
#ifdef SM_REPLAY
 /* Deterministic native integration playback; excluded from the player build. */
 joy=phase==1?(bx<pitchx?2:bx>pitchx?512:0):0;
 fire=(phase==0&&timer==0)||(phase==1&&timer==duration-5);
#endif
 update(fire,joy);draw=screen[front^1];render();while(((*(volatile u32*)0xdff004)&0x1ff00)!=0x12c00){}display(front^1);front^=1;while(((*(volatile u32*)0xdff004)&0x1ff00)==0x12c00){}}
}
