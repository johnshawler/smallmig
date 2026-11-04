/* SPDX-License-Identifier: 0BSD. Probe adapter built around the bare harness. */
.include "build/homebrew/constants.i"
.section .text
.global _start
_start:
    move.l %a0,%a4
    jsr -120(%a6)
    lea 0xdff000,%a5
    move.w #0x7fff,0x9a(%a5)
    move.w #0x7fff,0x96(%a5)
    move.w #0x7fff,0x9c(%a5)
    lea 66048(%a4),%a1    /* 10240-byte display/output plane */
    lea 65536(%a4),%a3    /* 256-byte zero page */
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
    /* A second distant calibration band keeps optical decoding accurate
       after adding hundreds of independently observed reference states. */
    lea _start+74048(%pc),%a2
    moveq #15,%d0
lower_cal_row:
    moveq #0,%d1
    btst #0,%d0
    beq lower_cal_black
    moveq #-1,%d1
lower_cal_black:
    moveq #9,%d2
lower_cal_long:
    move.l %d1,(%a2)+
    dbra %d2,lower_cal_long
    dbra %d0,lower_cal_row
    lea fixtures(%pc),%a0
    move.l #CASE_COUNT,%a4
next_case:
    move.b (%a0)+,10(%a3)
    move.b (%a0)+,12(%a3)
    move.b (%a0)+,18(%a3)
    move.b (%a0)+,19(%a3)
    move.b (%a0)+,20(%a3)
    move.b (%a0)+,22(%a3)
    move.b (%a0)+,31(%a3)
    move.b (%a0)+,32(%a3)
    move.b (%a0)+,33(%a3)
    move.b (%a0)+,256(%a3)
    moveq #0,%d0
    moveq #0,%d1
    moveq #0,%d2
    moveq #0,%d3
    moveq #0,%d4
    bsr translated_falling_move
    move.b 10(%a3),(%a1)+
    move.b 12(%a3),(%a1)+
    move.b 18(%a3),(%a1)+
    move.b 19(%a3),(%a1)+
    move.b 20(%a3),(%a1)+
    move.b 22(%a3),(%a1)+
    move.b 31(%a3),(%a1)+
    move.b 32(%a3),(%a1)+
    move.b 33(%a3),(%a1)+
    move.b %d0,(%a1)+
    move.b %d1,(%a1)+
    move.b %d2,(%a1)+
    move.b %d3,(%a1)+
    move.b %d4,(%a1)+
    move.b 256(%a3),(%a1)+
    lea -15(%a1),%a2
    moveq #14,%d5
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
    move.b #1,BUTTONS(%a3)
    move.b #0,DIFFICULTY(%a3)
    move.b #128,PLAYERX(%a3)
    move.b #88,PLAYERY(%a3)
    move.b #0,PLAYERX_SUB(%a3)
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
    bsr translated_falling_move
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
    move.l #98304,(%a1)+
    lea _start+96000(%pc),%a0
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
    lea _start+66048(%pc),%a1
    lea copper(%pc),%a0
    move.l %a1,%d0
    move.w %d0,6(%a0)
    swap %d0
    move.w %d0,2(%a0)
    lea _start+78000(%pc),%a2
    move.l %a2,%d0
    move.w %d0,14(%a0)
    move.w %d0,22(%a0)
    swap %d0
    move.w %d0,10(%a0)
    move.w %d0,18(%a0)
    lea 0x128(%a5),%a1
    moveq #5,%d0
null_sprites:
    move.l %a2,(%a1)+
    dbra %d0,null_sprites
    move.l %a0,0x80(%a5)
    move.w #0,0x88(%a5)
    move.w #0x8380,0x96(%a5) /* master, raster, copper */
    /* Probe output remains visible until right Ctrl (fire) enters the slice. */
wait_demo:
    btst #7,0xbfe001
    bne wait_demo
    move.b #0,BUTTONS(%a3)
    move.b #0,DIFFICULTY(%a3)
    move.b #128,PLAYERX(%a3)
    move.b #88,PLAYERY(%a3)
    move.b #0,PLAYERX_SUB(%a3)
    move.b #1,PLAYERFACING(%a3)
    lea _start+66048(%pc),%a0
    move.w #2559,%d0
clear_plane:
    clr.l (%a0)+
    dbra %d0,clear_plane
    /* Native boundary marks at source x limits, centered in 320-pixel display. */
    lea _start+66048+40*30(%pc),%a0
    move.w #151,%d0
walls:
    or.b #4,5(%a0)          /* logical x=45 */
    or.b #2,34(%a0)         /* logical x=278 */
    lea 40(%a0),%a0
    dbra %d0,walls
    move.w #0x123,0x180(%a5)
    move.w #0x0da6,0x1a2(%a5)
    move.w #0x0633,0x1a4(%a5)
    move.w #0x0fdb,0x1a6(%a5)
    lea sample(%pc),%a0
    move.l %a0,0xa0(%a5)
    move.w #16,0xa4(%a5)
    move.w #400,0xa6(%a5)
    move.w #0,0xa8(%a5)
    move.w #0x8021,0x96(%a5) /* native sprite and Paula DMA */
frame:
    move.l 4(%a5),%d0
    and.l #0x1ff00,%d0
    cmp.l #0x12c00,%d0
    bne frame
leave_line:
    move.l 4(%a5),%d0
    and.l #0x1ff00,%d0
    cmp.l #0x12c00,%d0
    beq leave_line
    moveq #0,%d0
    move.w 0xc(%a5),%d1
    btst #1,%d1
    beq no_right
    or.b #1,%d0
no_right:
    btst #9,%d1
    beq no_left
    or.b #2,%d0
no_left:
    move.b %d0,BUTTONS(%a3)
    bsr translated_falling_move
    /* Native renderer consumes ROM-derived x/y/facing, no NES PPU emulation. */
    lea sprite_right_0(%pc),%a0
    lea sprite_right_1(%pc),%a1
    tst.b PLAYERFACING(%a3)
    bne pose_ready
    lea sprite_left_0(%pc),%a0
    lea sprite_left_1(%pc),%a1
pose_ready:
    moveq #0,%d0
    move.b PLAYERX(%a3),%d0
    add.w #148,%d0         /* hardware origin 128 + centered NES offset 32 -12 */
    moveq #0,%d1
    move.b PLAYERY(%a3),%d1
    add.w #12,%d1          /* hardware origin 44 - character height 32 */
    bsr position_sprite
    add.w #16,%d0
    exg %a0,%a1
    bsr position_sprite
    exg %a0,%a1
    lea copper(%pc),%a2
    move.l %a0,%d0
    move.w %d0,14(%a2)
    swap %d0
    move.w %d0,10(%a2)
    move.l %a1,%d0
    move.w %d0,22(%a2)
    swap %d0
    move.w %d0,18(%a2)
    moveq #0,%d0
    btst #7,0xbfe001
    beq sound_on
    cmp.b #13,PLAYERX(%a3)
    bne not_left_wall
    btst #1,BUTTONS(%a3)
    bne sound_on
not_left_wall:
    cmp.b #246,PLAYERX(%a3)
    bne quiet
    btst #0,BUTTONS(%a3)
    beq quiet
sound_on:
    moveq #32,%d0
quiet:
    move.w %d0,0xa8(%a5)
    bra frame
position_sprite:
    move.w %d0,%d2
    lsr.w #1,%d2
    move.w %d1,%d3
    lsl.w #8,%d3
    or.w %d2,%d3
    move.w %d3,(%a0)
    move.w %d1,%d3
    add.w #32,%d3
    lsl.w #8,%d3
    move.w %d0,%d2
    and.w #1,%d2
    or.w %d2,%d3
    move.w %d3,2(%a0)
    rts
.balign 4
copper:
    .word 0xe0,0,0xe2,0
    .word 0x120,0,0x122,0
    .word 0x124,0,0x126,0
    .word 0xffff,0xfffe
failed:
    .byte 0
.balign 2
.include "build/homebrew/translated.s"
.include "build/homebrew/sprites.s"
.balign 4
sample:
    .rept 16
    .byte 96
    .endr
    .rept 16
    .byte -96
    .endr
fixtures:
    .incbin "build/homebrew/fixtures.bin"
.balign 4
rom_prg:
    .incbin "build/homebrew/rom-prg.bin"
