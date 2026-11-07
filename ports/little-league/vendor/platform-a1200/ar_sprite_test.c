/* Original sprite/scroll fixture, no game data. Tests actual planar composition
 * and Copper output; times only snapshot + composition + list/publication work.
 * Fast code/data, Chip DMA output, active PAL display and Paula sample DMA. */
#include <stdint.h>
#include "platform.h"
#include "display.h"
#include "../runtime/arender.h"
static Nes n;
static uint8_t chr[8192];
static int8_t wave[128] __attribute__((aligned(4),section(".chipbuf")));
extern uint32_t ar_sprite_cache_stats[4];
static uint32_t hash=2166136261u;
static void word(unsigned reg,uint16_t value){*(volatile uint16_t*)(0xd00000+reg)=value;}
static void value(unsigned reg,uint32_t v){word(reg,v>>16);word(reg+2,v);}
static void prepare(unsigned frame,ArRegion *r)
{
    for(unsigned i=0;i<256;i++)n.ppu.oam[i]=0xff;
    for(unsigned i=0;i<64;i++){
        n.ppu.oam[4*i]=(i/9)*28+8;
        n.ppu.oam[4*i+1]=i%16;
        n.ppu.oam[4*i+2]=(i&3)|((i&1)?0x20:0)|((i&2)?0x40:0)|((i&4)?0x80:0);
        n.ppu.oam[4*i+3]=(i%9)*27+(frame/2)%7;
    }
    r->y0=0;r->y1=239;r->vl=r->tx=0;r->fx=frame%8;
    r->rend=r->bg_en=r->sp_en=1;r->min_bg=r->min_sp=8;
    r->mirror=2;r->chr_lo=(frame>>3)&1;r->chr_hi=r->chr_lo^1;
    r->large=(frame>>4)&1;
    for(unsigned e=0;e<32;e++)r->pal[e]=(e*7+3)&63;
}
void ar_sprite_test_main(void)
{
    word(6,0x1000);
    n.map.chr=chr;n.map.mirror=2;
    for(unsigned bank=0;bank<2;bank++)for(unsigned tile=0;tile<256;tile++)for(unsigned y=0;y<8;y++)for(unsigned x=0;x<8;x++){
        unsigned v=tile?((x+3*y+tile+bank)&3):0;
        for(unsigned k=0;k<2;k++)if(v&(1<<k))chr[bank*4096+tile*16+y+k*8]|=0x80>>x;
    }
    for(unsigned i=0;i<2048;i++)n.ppu.nt[i]=(i%1024<960)?i%15+1:0xe4;
    display_init();ar_init();
    word(6,0x1001);
    ArRegion r={0};
    /* Prewarm both buffers outside the timed window, including pattern banks. */
    for(unsigned f=0;f<32;f++){
        plat_wait_vbl();prepare(f,&r);ar_begin_frame(&n);ar_log_region(&n,&r);ar_end_frame(&n,&ar_out);
        while(!display_frame(0,0))plat_wait_vbl();
    }
    word(6,0x1002);
    for(unsigned i=0;i<128;i++)wave[i]=(i&32)?32:-32;
    *(volatile uint32_t*)0xdff0a0=(uint32_t)wave;
    *(volatile uint16_t*)0xdff0a4=64;*(volatile uint16_t*)0xdff0a6=124;
    *(volatile uint16_t*)0xdff0a8=0;*(volatile uint16_t*)0xdff096=0x8201;
    for(unsigned i=0;i<4;i++)ar_sprite_cache_stats[i]=0;
    uint32_t sum=0,maximum=0;
    for(unsigned f=0;f<64;f++){
        plat_wait_vbl();prepare(f,&r);
        uint32_t tick=plat_tick_count;uint16_t before=plat_eclock();
        ar_begin_frame(&n);ar_log_region(&n,&r);ar_end_frame(&n,&ar_out);
        /* Expand before publication switches the target sprite-layer set.
         * Hashing is deliberately outside the renderer timing interval. */
        uint32_t elapsed=(uint16_t)(before-plat_eclock());
        if(plat_tick_count-tick>4){word(0x08,0xbad);for(;;){};}
        for(unsigned k=0;k<4;k++)for(unsigned y=0;y<240;y++)for(unsigned i=0;i<32;i++)
            hash=(hash^AR_SPR(k,y)[i])*16777619u;
        before=plat_eclock();
        while(!display_frame(0,0))plat_wait_vbl();
        elapsed+=(uint16_t)(before-plat_eclock());
        sum+=elapsed;if(elapsed>maximum)maximum=elapsed;
        if((f&15)==15)word(6,0x2000+f);
    }
    plat_wait_vbl();plat_wait_vbl();
    value(0x10,sum);value(0x14,maximum);value(0x18,hash);
    for(unsigned i=0;i<4;i++)value(0x20+4*i,ar_sprite_cache_stats[i]);
    word(0,0x534d);word(2,5);
    for(;;)__asm__ volatile("stop #0x2000");
}
