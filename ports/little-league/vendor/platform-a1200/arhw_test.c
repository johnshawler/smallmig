/* arhw_test.c - ARHW_TEST: hardware test of the stage 2b display (display_ar2.c) without emulation.  Synthetic persistent bitmaps (stride 96, guard bytes), sprite layer and
 * exact layers are filled with pixel formulas, a region list covering the cases of the Copper builder (scroll 0 / N = 0 / N = 511 / odd fine X, row wrap restart, exact, blank, palette
 * changes, line > 255) is turned into a Copper list and shown.  tests/amiga/arhw_expect.py computes the same picture; the screenshot must equal it pixel for pixel. */
#include <stdint.h>
#include "platform.h"
#include "display.h"
#include "../runtime/arender.h"
#include "display_ar2.h"

#define BROW AR_BROW
#define NCFG 2
static uint8_t bmp[NCFG * 4 * 512 * BROW] __attribute__((aligned(4), section(".chipbuf")));
static uint8_t spr[4 * 240 * 32 + 4] __attribute__((aligned(4), section(".chipbuf")));
static uint8_t xp1[4 * 240 * 32 + 4] __attribute__((aligned(4), section(".chipbuf")));
static uint8_t xp2[4 * 240 * 32 + 4] __attribute__((aligned(4), section(".chipbuf")));
static uint32_t list[2048] __attribute__((aligned(4), section(".chipbuf")));
static ArFrame frame;
#ifdef ARHW_STANDALONE
static uint32_t bus_scratch[4096] __attribute__((aligned(4), section(".chipbuf")));
/* Position-independent 68020 loop, copied to Fast RAM: 4096 Chip long writes.
 * This measures display bus contention, not full-game speed. */
static unsigned bus_ticks(void)
{
    static const uint16_t code[] = {0x206f,4,0x303c,4095,0x223c,0x55aa,0x33cc,
                                    0x20c1,0x51c8,0xfffc,0x4e75};
    volatile uint16_t *fast = (volatile uint16_t*)0x200000;
    for (unsigned i=0;i<sizeof code/sizeof code[0];i++) fast[i]=code[i];
    for (unsigned i=0;i<sizeof code/sizeof code[0];i++) if (fast[i]!=code[i]) return 0;
    unsigned best=65535;
    for (unsigned i=0;i<3;i++) {
        plat_wait_vbl();
        while (((*(volatile uint32_t*)0xdff004 >> 8)&511) != plat_vstart) {}
        uint16_t before=plat_eclock();
        ((void (*)(void*))0x200000)(bus_scratch);
        unsigned elapsed=(uint16_t)(before-plat_eclock());
        if (elapsed<best) best=elapsed;
    }
    return best;
}
#endif

/* pixel formulas (mirrored in tests/amiga/arhw_expect.py) */
static unsigned bgv(unsigned c, unsigned r, unsigned x) { return (x + 3 * r + 5 * c + ((x >> 4) ^ (r >> 1))) & (c ? 7 : 15); }   /* configuration 1 shows only values 0..7 */
static unsigned spv(unsigned y, unsigned x) { return ((x + y) % 5 < 2) ? ((x * 3 + y) & 7) : 0; }
static unsigned x1v(unsigned y, unsigned x) { return (x * 5 + y * 3) & 15; }
static unsigned x2v(unsigned y, unsigned x) { return (x % 3) ? ((x + 2 * y) & 15) : 0; }

static void put(uint8_t *row, unsigned x, unsigned bit) { if (bit) row[x >> 3] |= (uint8_t)(0x80 >> (x & 7)); }

void arhw_test_main(void)
{
    display_init();
    for (unsigned c = 0; c < NCFG; c++) for (unsigned r = 0; r < 512; r++) {
        for (unsigned x = 0; x < 512; x++) { unsigned v = bgv(c, r, x); for (unsigned k = 0; k < 4; k++) put(bmp + ((c * 4 + k) * 512 + r) * BROW, x, (v >> k) & 1); }
        for (unsigned k = 0; k < 4; k++) { uint8_t *row = bmp + ((c * 4 + k) * 512 + r) * BROW; for (unsigned i = 0; i < BROW-64; i++) row[64 + i] = row[i]; }
    }
    for (unsigned y = 0; y < 240; y++) for (unsigned x = 0; x < 256; x++) {
        unsigned s = spv(y, x), a = x1v(y, x), b = x2v(y, x);
        for (unsigned k = 0; k < 4; k++) { put(spr + (k * 240 + y) * 32, x, (s >> k) & 1); put(xp1 + (k * 240 + y) * 32, x, (a >> k) & 1); put(xp2 + (k * 240 + y) * 32, x, (b >> k) & 1); }
    }
    static const struct { int16_t y0, y1; uint8_t kind, cfg; uint16_t row0; uint8_t bytex, fx, pv; } T[] = {
        {   0,   2, AR_BG, 0,   0,  0, 0, 0 },
        {   3,   5, AR_BG, 0,  13,  2, 1, 0 },
        {   6,   8, AR_BG, 0,  26,  4, 2, 0 },
        {   9,  11, AR_BG, 0,  39,  6, 3, 0 },
        {  12,  14, AR_BG, 0,  52,  8, 4, 0 },
        {  15,  17, AR_BG, 0,  65, 10, 5, 0 },
        {  18,  20, AR_BG, 0,  78, 12, 6, 0 },
        {  21,  23, AR_BG, 0,  91, 14, 7, 0 },
        {  24,  26, AR_BG, 0, 104, 17, 0, 0 },
        {  27,  29, AR_BG, 0, 117, 19, 1, 0 },
        {  30,  32, AR_BG, 0, 130, 21, 2, 0 },
        {  33,  35, AR_BG, 0, 143, 23, 3, 0 },
        {  36,  38, AR_BG, 0, 156, 25, 4, 0 },
        {  39,  41, AR_BG, 0, 169, 27, 5, 0 },
        {  42,  44, AR_BG, 0, 182, 29, 6, 0 },
        {  45,  47, AR_BG, 0, 195, 31, 7, 0 },
        {  48,  50, AR_BG, 1, 208, 34, 0, 0 },
        {  51,  53, AR_BG, 1, 221, 36, 1, 0 },
        {  54,  56, AR_BG, 1, 234, 38, 2, 0 },
        {  57,  59, AR_BG, 1, 247, 40, 3, 0 },
        {  60,  62, AR_BG, 1, 260, 42, 4, 0 },
        {  63,  65, AR_BG, 1, 273, 44, 5, 0 },
        {  66,  68, AR_BG, 1, 286, 46, 6, 0 },
        {  69,  71, AR_BG, 1, 299, 48, 7, 0 },
        {  72,  74, AR_BG, 1, 312, 51, 0, 0 },
        {  75,  77, AR_BG, 1, 325, 53, 1, 0 },
        {  78,  80, AR_BG, 1, 338, 55, 2, 0 },
        {  81,  83, AR_BG, 1, 351, 57, 3, 0 },
        {  84,  86, AR_BG, 1, 364, 59, 4, 0 },
        {  87,  89, AR_BG, 1, 377, 61, 5, 0 },
        {  90,  92, AR_BG, 1, 390, 63, 6, 0 },
        {  93,  95, AR_BG, 1, 403,  1, 7, 0 },
        {  96, 107, AR_BG,    0, 500, 16, 0, 2 },
        { 108, 127, AR_BG,    0,   0, 16, 0, 3 },
        { 128, 143, AR_EXACT, 0,   0,  0, 0, 3 },
        { 144, 159, AR_BLANK, 0,   0,  0, 0, 4 },
        { 160, 191, AR_BG,    1,   0, 31, 5, 4 },
        { 192, 215, AR_BG,    0, 200,  8, 0, 5 },
        { 216, 239, AR_BG,    0, 224,  8, 0, 6 },     /* first line > 255 on PAL (Copper wait wrap) */
    };
    frame.nreg = sizeof(T) / sizeof(T[0]);
    for (unsigned i = 0; i < (unsigned)frame.nreg; i++) {
        ArRegion *r = &frame.reg[i];
        r->y0 = T[i].y0; r->y1 = T[i].y1; r->kind = T[i].kind; r->cfg = T[i].cfg; r->row0 = T[i].row0; r->bytex = T[i].bytex; r->fx = T[i].fx; r->gray = 0; r->emph = 0;
        for (unsigned e = 0; e < 32; e++) r->pal[e] = T[i].pv >= 6 ? (uint8_t)((e * 11 + 9 + 5 * T[i].pv) & 0x3F) : (uint8_t)((e * 7 + 3 + ((e % 8 == (unsigned)T[i].pv % 8) ? 5 * T[i].pv : 0) + (e == 17 ? i : 0)) & 0x3F);
    }
    static uint32_t used[sizeof(T) / sizeof(T[0])];
    for (unsigned i = 0; i < (unsigned)frame.nreg; i++) used[i] = (T[i].cfg ? 0x000000EFu : 0x0000FFFFu) | 0x00FE0000u;   /* palette entries shown: cfg 1: 0,1,2,3,5,6,7 (4 = backdrop), cfg 0: 0..15; sprites 17..23 */
    Ar2Mem m = { bmp, spr, xp1, xp2, BROW, used };
    uint32_t *p = list;
    *p++ = (0x1FCu << 16) | AR2_FMODE;
    *p++ = (0x100u << 16) | 0x0611;           /* 8 planes, dual playfield, colour */
    *p++ = (0x104u << 16) | 0x0040;           /* playfield 2 in front */
    *p++ = (0x092u << 16) | AR2_DDF_START;
    *p++ = (0x094u << 16) | AR2_DDF_STOP;
    ar2_build(p, 2048 - 5, &frame, &m);
    plat_cop_ptr[0] = (uint32_t)list; plat_cop_ptr[1] = (uint32_t)list;
    plat_show(0);
#ifdef ARHW_STANDALONE
    plat_wait_vbl(); plat_wait_vbl();
    *(volatile uint16_t*)0xd00004=(uint16_t)bus_ticks();
    *(volatile uint16_t*)0xd00000=0x534d;
    *(volatile uint16_t*)0xd00002=5;
#endif
    for (;;) __asm__ volatile("stop #0x2000");
}
