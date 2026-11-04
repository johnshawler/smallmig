/* GNU m68k syntax. All runtime references are position independent. */
.section .text
.global _start
_start:
    .ascii "DOS\0"
    .long 0,880
boot:
    move.l #16384,%d0
    move.l #0x10002,%d1       /* MEMF_CHIP | MEMF_CLEAR */
    jsr -198(%a6)            /* exec.AllocMem */
    tst.l %d0
    beq alloc_failed
    move.l %d0,%a0
    lea _start(%pc),%a1
    move.w #255,%d1
copy:
    move.l (%a1)+,(%a0)+
    dbra %d1,copy
    move.l %d0,%a0
    lea copied-_start(%a0),%a0
    jmp (%a0)
alloc_failed:
    moveq #-1,%d0
    rts
copied:
    jsr -120(%a6)            /* exec.Disable; takeover until reset */
    lea 0xdff000,%a5
    move.w #0x7fff,0x9a(%a5)
    move.w #0x7fff,0x96(%a5)
    move.w #0x7fff,0x9c(%a5)
    move.w #0x1200,0x100(%a5)     /* one blank bitplane; sprite on solid backdrop */
    move.w #0,0x102(%a5)
    move.w #0,0x104(%a5)
    move.w #0,0x106(%a5)     /* AGA palette bank zero */
    move.w #0x11,0x10c(%a5)     /* AGA sprite palette bank 16 */
    move.w #0,0x1fc(%a5)     /* original 16-bit DMA fetch mode */
    move.w #0,0x1e4(%a5)
    move.w #0x2c81,0x8e(%a5)
    move.w #0x2cc1,0x90(%a5)
    move.w #0x38,0x92(%a5)
    move.w #0xd0,0x94(%a5)
    move.w #0x123,0x180(%a5)
    move.w #0x0fc,0x1a2(%a5) /* sprite color 17 */
    lea _start+1024(%pc),%a0 /* cleared null sprite data */
    lea 0x124(%a5),%a1
    moveq #6,%d0
null_sprites:
    move.l %a0,(%a1)+
    dbra %d0,null_sprites
    lea sprite(%pc),%a2
    lea copper(%pc),%a0
    move.l %a2,%d0
    move.w %d0,6(%a0)
    swap %d0
    move.w %d0,2(%a0)
    lea _start+1024(%pc),%a1
    move.l %a1,%d0
    move.w %d0,14(%a0)
    swap %d0
    move.w %d0,10(%a0)
    move.l %a0,0x80(%a5)
    move.w #0,0x88(%a5)
    lea sample(%pc),%a0
    move.l %a0,0xa0(%a5)
    move.w #16,0xa4(%a5)
    move.w #400,0xa6(%a5)
    move.w #0,0xa8(%a5)
    move.w #0x83a1,0x96(%a5) /* master, raster, copper, sprites, audio0 */
    move.w #272,%d4          /* hardware x: visible origin ~128 */
    move.w #150,%d5          /* hardware y: visible origin 44 */
frame:
    move.l 4(%a5),%d0
    and.l #0x1ff00,%d0
    cmp.l #0x12c00,%d0       /* PAL raster line 300 */
    bne frame
leave_line:
    move.l 4(%a5),%d0
    and.l #0x1ff00,%d0
    cmp.l #0x12c00,%d0
    beq leave_line
    move.w 0xc(%a5),%d0     /* JOY1DAT */
    btst #1,%d0
    beq no_right
    addq.w #2,%d4
no_right:
    btst #9,%d0
    beq no_left
    subq.w #2,%d4
no_left:
    move.w %d0,%d1
    lsr.w #1,%d1
    eor.w %d1,%d0
    btst #0,%d0
    beq no_down
    addq.w #2,%d5
no_down:
    btst #8,%d0
    beq no_up
    subq.w #2,%d5
no_up:
    cmp.w #128,%d4
    bge xmin
    move.w #128,%d4
xmin:
    cmp.w #432,%d4
    ble xmax
    move.w #432,%d4
xmax:
    cmp.w #44,%d5
    bge ymin
    move.w #44,%d5
ymin:
    cmp.w #239,%d5
    ble ymax
    move.w #239,%d5
ymax:
    move.w %d5,%d0
    lsl.w #8,%d0
    move.w %d4,%d1
    lsr.w #1,%d1
    or.w %d1,%d0
    move.w %d0,(%a2)
    move.w %d5,%d0
    add.w #16,%d0
    lsl.w #8,%d0
    move.w %d4,%d1
    and.w #1,%d1
    or.w %d1,%d0
    move.w %d0,2(%a2)
    moveq #0,%d0
    btst #7,0xbfe001         /* port 1 fire, active low */
    bne quiet
    moveq #32,%d0
quiet:
    move.w %d0,0xa8(%a5)
    bra frame
.balign 4
copper:                     /* reset sprite pointer every frame */
    .word 0x120,0,0x122,0
    .word 0xe0,0,0xe2,0
    .word 0xffff,0xfffe
sprite:
    .word 0x9688,0xa600
    .rept 16
    .word 0xffff,0
    .endr
    .long 0
sample:
    .rept 16
    .byte 96
    .endr
    .rept 16
    .byte -96
    .endr
end_payload:
