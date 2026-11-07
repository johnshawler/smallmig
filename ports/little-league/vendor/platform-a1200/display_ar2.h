/* display_ar2.h - hardware side of arender stage 2b (see display_ar2.c) */
#ifndef DISPLAY_AR2_H
#define DISPLAY_AR2_H
#include <stdint.h>
#include "../runtime/arender.h"
/* Wider AGA fetches release Chip RAM bus slots to the CPU. The hidden group
 * before the visible window must grow with the fetch width, and all pointers,
 * guard bytes, modulos and extended BPLCON1 delay bits must agree. */
#ifdef AR2_FETCH32
#define AR2_FMODE 1
#define AR2_DDF_START 0x30
#define AR2_DDF_STOP 0xB0
#define AR2_FETCH_PIXELS 32
#define AR2_FETCH_SHIFT 5
#define AR2_PAD_BYTES 4
#define AR2_FETCH_BYTES 36
#else
#define AR2_FMODE 0
#define AR2_DDF_START 0x40
#define AR2_DDF_STOP 0xC0
#define AR2_FETCH_PIXELS 16
#define AR2_FETCH_SHIFT 4
#define AR2_PAD_BYTES 2
#define AR2_FETCH_BYTES 34
#endif
typedef struct { uint8_t *bmp, *spr, *xpf1, *xpf2; unsigned brow; const uint32_t *used; } Ar2Mem;   /* bitmap base (cfg,plane,row) with row stride brow, sprite layer, exact-line playfields */
int ar2_build(uint32_t *list, unsigned max, const ArFrame *f, const Ar2Mem *m);
#endif
