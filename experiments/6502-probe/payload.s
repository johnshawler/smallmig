/* SPDX-License-Identifier: 0BSD. Probe adapter built around the bare harness. */
.include "build/probe/fixture-count.i"
.section .text
.global _start
_start:
    move.l %a0,%a4
    jsr -120(%a6)
    lea 0xdff000,%a5
    move.w #0x7fff,0x9a(%a5)
    move.w #0x7fff,0x96(%a5)
    move.w #0x7fff,0x9c(%a5)
    lea 16384(%a4),%a1    /* 10240-byte display/output plane */
    lea 30000(%a4),%a3    /* 256-byte zero page */
    /* Calibration: sixteen full-width alternating white/black rows. */
    moveq #15,%d0
cal_row:
    moveq #0,%d1
    btst #0,%d0
    beq cal_black
    moveq #-1,%d1
cal_black:
    moveq #9,%d2
cal_long:
    move.l %d1,(%a1)+
    dbra %d2,cal_long
    dbra %d0,cal_row
    lea fixtures(%pc),%a0
    move.l #CASE_COUNT,%a4
next_case:
    move.l %a3,%a2
    moveq #4,%d0
copy_initial:
    move.b (%a0)+,(%a2)+
    dbra %d0,copy_initial
    moveq #0,%d0
    moveq #0,%d1
    moveq #0,%d2
    moveq #0,%d3
    moveq #0,%d4
    bsr translated_step
    move.l %a3,%a2
    moveq #4,%d5
copy_actual:
    move.b (%a2)+,(%a1)+
    dbra %d5,copy_actual
    move.b %d0,(%a1)+
    move.b %d1,(%a1)+
    move.b %d2,(%a1)+
    move.b %d3,(%a1)+
    move.b %d4,(%a1)+
    lea -10(%a1),%a2
    moveq #9,%d5
compare_actual:
    move.b (%a2)+,%d6
    cmp.b (%a0)+,%d6
    beq match
    lea failed(%pc),%a6
    move.b #1,(%a6)
match:
    dbra %d5,compare_actual
    subq.l #1,%a4
    cmpa.l #0,%a4
    bne next_case
    /* Benchmark 20,000 updates, including native call/loop overhead.
       CPU code/data in Chip RAM, all display/audio DMA disabled. */
    move.b #0,(%a3)
    move.b #1,1(%a3)
    move.b #128,2(%a3)
    move.b #0,3(%a3)
    move.b #0,4(%a3)
    move.b #0,0xbfee01
    move.b #0,0xbfef01
    move.b #0x7f,0xbfed01
    move.b 0xbfed01,%d0
    move.b #255,0xbfe401
    move.b #255,0xbfe501
    move.b #255,0xbfe601
    move.b #255,0xbfe701
    move.l #20000,%a4
    move.b #0x51,0xbfef01   /* B counts A underflows */
    move.b #0x11,0xbfee01   /* A counts PAL E clock */
bench_loop:
    bsr translated_step
    subq.l #1,%a4
    cmpa.l #0,%a4
    bne bench_loop
    move.b #0,0xbfee01
    move.b #0x40,0xbfef01
    moveq #0,%d0
    move.b 0xbfe701,%d0
    lsl.l #8,%d0
    move.b 0xbfe601,%d0
    lsl.l #8,%d0
    move.b 0xbfe501,%d0
    lsl.l #8,%d0
    move.b 0xbfe401,%d0
    not.l %d0
    move.l #0x50524f42,(%a1)+ /* PROB */
    move.l %d0,(%a1)+        /* elapsed CIA ticks */
    move.l #20000,(%a1)+
    move.l #32768,(%a1)+
    lea _start+32000(%pc),%a0
    move.l (%a0)+,(%a1)+    /* free Chip before allocation */
    move.l (%a0)+,(%a1)+    /* free Fast before allocation */
    move.l (%a0)+,(%a1)+    /* free Chip after allocation */
    move.l (%a0)+,(%a1)+    /* free Fast after allocation */
    /* Same basic one-plane AGA-compatible display setup as the harness. */
    move.w #0x1200,0x100(%a5)
    move.w #0,0x102(%a5)
    move.w #0,0x104(%a5)
    move.w #0,0x106(%a5)
    move.w #0x11,0x10c(%a5)
    move.w #0,0x1fc(%a5)
    move.w #0,0x1e4(%a5)
    move.w #0x2c81,0x8e(%a5)
    move.w #0x2cc1,0x90(%a5)
    move.w #0x38,0x92(%a5)
    move.w #0xd0,0x94(%a5)
    move.w #0x030,0x180(%a5)
    lea failed(%pc),%a0
    tst.b (%a0)
    beq passed
    move.w #0x900,0x180(%a5)
passed:
    move.w #0xfff,0x182(%a5)
    lea _start+16384(%pc),%a1
    lea copper(%pc),%a0
    move.l %a1,%d0
    move.w %d0,6(%a0)
    swap %d0
    move.w %d0,2(%a0)
    move.l %a0,0x80(%a5)
    move.w #0,0x88(%a5)
    move.w #0x8380,0x96(%a5) /* master, raster, copper */
forever:
    bra forever
.balign 4
copper:
    .word 0xe0,0,0xe2,0,0xffff,0xfffe
failed:
    .byte 0
.balign 2
.include "build/probe/translated.s"
translated_end:
.balign 4
fixtures:
    .incbin "build/probe/fixtures.bin"
