/* Functional CPU-only execution of the real translated payload. No Amiga OS,
 * display timing, Paula DMA or physical performance claim is made by this tool. */
#include "../runtime/rt.h"
#include "../runtime/arender.h"
#include "../runtime/audio_words.h"
#include <stddef.h>
static const struct { unsigned f, m; } steps[]={
#include "testinput.inc"
};
static AudioWords words;
static uint64_t from;
static int8_t pcm[1024];
uint32_t native_pcm_hash;
const uint32_t native_hw_storage_bytes = AR_HW_BYTES + 4;
void native_init(void){
    aw_init(&words,11803,21423809u,39375000u,124);
    from=0;
    native_pcm_hash=2166136261u;
}
uint8_t native_input(int port,long frame){
    unsigned m=0;
    for(unsigned i=0;i<sizeof steps/sizeof steps[0];i++){
        if(steps[i].f<=(unsigned)frame) m=steps[i].m; else break;
    }
    if(port) m>>=16;
    return (uint8_t)(((m&0x100)?1:0)|((m&1)?2:0)|(m&0xfc));
}
void native_frame(long frame){
    (void)frame;
    /* rt_sync already finished the planar composition before this hook. */
    ar_hw_shown();
    unsigned n=aw_next(&words);
    uint64_t to=rt_div3(nes.ppu.dots)-2;
    apu_render8(&rt_apu,from,to,pcm,2*n);
    from=to;
    native_pcm_hash=(native_pcm_hash^(n>>8))*16777619u;
    native_pcm_hash=(native_pcm_hash^(n&255))*16777619u;
    for(unsigned i=0;i<2*n;i++) native_pcm_hash=(native_pcm_hash^(uint8_t)pcm[i])*16777619u;
}
const uint32_t native_layout[]={
    offsetof(Rt,frame_hook),offsetof(Rt,input_hook),offsetof(Rt,frames_done),
    offsetof(Nes,ram),offsetof(Nes,ppu)+offsetof(Ppu,oam),
    offsetof(Nes,ppu)+offsetof(Ppu,pal),offsetof(Nes,ppu)+offsetof(Ppu,nt)
};
