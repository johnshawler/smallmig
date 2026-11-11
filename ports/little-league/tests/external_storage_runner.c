/* Exercise the real host driver with both layer sets and guarded external RAM.
 * Build once normally and once with AR_NO_STATIC; compare results. */
#include "../vendor/runtime/arender.h"
#include "../vendor/runtime/rt.h"
#include <assert.h>
#include <stdint.h>
#include <string.h>
static void storage_run(long n);
extern int rt_ppu_check;
static unsigned seen_selections;
#define main host_main
#define rt_run_interp storage_run
#include "../vendor/tools/rt_host.c"
#undef main
#undef rt_run_interp
#ifdef AR_NO_STATIC
static struct {
    uint32_t before[16];
    uint8_t bytes[AR_HW_BYTES + 4];
    uint32_t after[16];
} guarded __attribute__((aligned(4)));
#endif
static void check_storage(void){
#ifdef AR_NO_STATIC
    for(unsigned i=0;i<16;i++) assert(guarded.before[i]==0xa5a55a5a && guarded.after[i]==0xa5a55a5a);
    uintptr_t lo=(uintptr_t)guarded.bytes, hi=lo+AR_HW_BYTES;
    assert((uintptr_t)ar_hw.bmp==lo);
    const uint8_t *layers[]={ar_hw.spr,ar_hw.xpf1,ar_hw.xpf2};
    for(unsigned i=0;i<3;i++) assert((uintptr_t)layers[i]>=lo && (uintptr_t)layers[i]+4*240*AR_STRIDE<=hi);
#endif
}
static void storage_frame(long f){
    seen_selections |= 1u << ar_hw.sel;
    frame(f);
    check_storage();
    /* PPU_CHECK already swaps once in rt_sync after pixel comparison. */
    if(!rt_ppu_check) ar_hw_shown();
    check_storage();
}
static void storage_run(long n){
    rt.frame_hook=storage_frame;
    rt_run_interp(n);
}
int main(int argc,char **argv){
#ifdef AR_NO_STATIC
    for(unsigned i=0;i<16;i++) guarded.before[i]=guarded.after[i]=0xa5a55a5a;
    ar_hw_setmem(guarded.bytes);
#endif
    int result=host_main(argc,argv);
    check_storage();
    assert(seen_selections == 3);
    fprintf(stderr,"STORAGE: both layer sets observed, guards intact\n");
    return result;
}
