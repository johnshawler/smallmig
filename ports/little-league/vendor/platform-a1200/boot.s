| boot.s - Little League Baseball Amiga 1200 bootblock (KS 3.x, 68020+).  Must stay <= 1024 bytes.
|
| Entered by the OS strap with A6 = ExecBase, A1 = trackdisk IOStdReq (open, DF0:).
| 0. CPU check: 68040/68060 are refused (cyan screen) - the cache handling below is the 68020/68030 one.
| 1. AllocMem(len, MEMF_CHIP) a staging buffer (wherever the OS has room).
| 2. trackdisk CMD_READ: disk byte offset 1024 .. 1024+len  -> staging buffer.
| 3. TD_MOTOR off.
| 4. Supervisor(): mask all interrupts, finish the Blitter, switch off all DMA, clear + disable the caches, copy the staging buffer to
|    PAYLOAD_BASE (0x800) with a relocator that runs from 0x200 (memmove: ascending if dst < src, else descending), jump to 0x800.
|    The OS is never used again.
| Failure (screen turns a solid colour, machine hangs):
|    magenta = AllocMem failed (payload too big for free chip RAM), red = disk read error, cyan = 68040/68060.
|
| `payload_len` (offset 20) is patched by tools/mkdisk.py (payload size rounded up to a multiple of 512).
    .ifdef  FASTRAM
    .ifndef FAST_BASE
    .equ    FAST_BASE, 0x200000
    .endif
    .equ    PAYLOAD_BASE, FAST_BASE    | selected 8 MB fast-memory region (Z2 or accelerator-local)
    .else
    .equ    PAYLOAD_BASE, 0x800
    .endif
    .equ    RELOC_ADDR,   0x200

    .text
    .long   0x444F5300          | 'DOS\0'
    .long   0                   | checksum (filled in by mkadf.py)
    .long   880                 | root block
entry:                          | offset 12
    bra.s   start
    .word   0
    .long   0x4C4C4241          | offset 16: marker 'LLBA' (checked by mkdisk.py)
payload_len:
    .long   0                   | offset 20: patched
    .ifdef RELOCATE
    .ascii  "RLOC"
runtime_len: .long 0
link_base:   .long 0
reloc_off:   .long 0
reloc_count: .long 0
    .endif

start:
    move.l  %a1,%a4             | a4 = IO request
    move.w  296(%a6),%d0        | ExecBase->AttnFlags: bit 3 = 68040, bit 7 = 68060
    move.w  #0x00FF,%d1         | cyan
    .ifdef CACHE040
    move.w  %d0,%d2
    andi.w  #0x0088,%d2         | 68040 or 68060; both use the explicit cache path
    beq     fail
    .else
    btst    #3,%d0
    bne     fail
    btst    #7,%d0
    bne     fail
    .endif
    .ifdef CACHE030
    btst    #2,%d0             | this optional image uses full-68030 MMU registers
    beq     fail
    .endif
    .ifdef  FASTRAM
    .ifdef RELOCATE
    move.l  runtime_len(%pc),%d0
    moveq   #4,%d1              | MEMF_FAST: let Exec choose the actual accelerator RAM
    jsr     -198(%a6)
    move.l  %d0,%a3
    tst.l   %d0
    beq     nofast
    .else
    | Scan ExecBase->MemList for an 8 MB fast-memory region at the linked base.
    move.l  322(%a6),%a0        | MemList.lh_Head
1:  move.l  (%a0),%d0           | ln_Succ (0 = end of list)
    beq.s   nofast
    btst    #2,15(%a0)          | mh_Attributes (word at 14): MEMF_FAST
    beq.s   2f
    cmp.l   #PAYLOAD_BASE+0x100,20(%a0)   | mh_Lower (the MemHeader itself sits at the start of the region)
    bhi.s   2f
    cmp.l   #PAYLOAD_BASE+0x800000,24(%a0)   | mh_Upper
    bcc.s   3f
2:  move.l  %d0,%a0
    bra.s   1b
3:
    .endif
    .endif
    move.l  payload_len(%pc),%d7
    move.l  %d7,%d0
    moveq   #2,%d1              | MEMF_CHIP
    jsr     -198(%a6)           | AllocMem
    move.l  %d0,%d6             | d6 = staging buffer
    beq   fail_mem
    move.w  #2,28(%a4)          | io_Command = CMD_READ
    move.l  %d7,36(%a4)         | io_Length
    move.l  %d6,40(%a4)         | io_Data
    move.l  #1024,44(%a4)       | io_Offset (payload starts at ADF byte 1024)
    move.l  %a4,%a1
    jsr     -456(%a6)           | DoIO
    tst.b   31(%a4)             | io_Error
    bne   fail_read
    move.w  #9,28(%a4)          | TD_MOTOR
    clr.l   36(%a4)             | io_Length = 0 -> motor off
    move.l  %a4,%a1
    jsr     -456(%a6)
    .ifdef RELOCATE
    move.l  reloc_count(%pc),%d2
    move.l  reloc_off(%pc),%d3
    move.l  link_base(%pc),%d4
    .endif
    lea     super(%pc),%a5
    jsr     -30(%a6)            | Supervisor(a5)  - never returns

    .ifdef  FASTRAM
nofast:                         | no suitable fast RAM: intuition DisplayAlert with the message, then wait
    lea     intname(%pc),%a1
    moveq   #0,%d0
    jsr     -552(%a6)           | OpenLibrary("intuition.library")
    tst.l   %d0
    beq.s   9f
    move.l  %d0,%a6
    moveq   #0,%d0              | RECOVERY_ALERT
    lea     alertmsg(%pc),%a0
    moveq   #40,%d1             | height
    jsr     -90(%a6)            | DisplayAlert
9:  move.w  #0x0FF0,%d1         | yellow screen if no alert could be shown
    bra   fail
intname: .asciz "intuition.library"
alertmsg:
    .byte   0,40,16
    .ifdef RELOCATE
    .asciz  "Little League Baseball needs more free FAST RAM"
    .else
    .asciz  "Little League Baseball needs 8 MB FAST at linked base"
    .endif
    .byte   1                   | another line follows
    .byte   0,40,32
    .ifdef RELOCATE
    .asciz  "(At least 4 MB FAST recommended)"
    .else
    .asciz  "(A1200 with an 8 MB board; none found)"
    .endif
    .byte   0                   | last line
    .even
    .endif

fail_mem:
    move.w  #0x0F0F,%d1
    bra.s   fail
fail_read:
    move.w  #0x0F00,%d1
fail:
    move.w  #0x7FFF,0xDFF096    | DMA off -> screen = COLOR00
    move.w  #0x7FFF,0xDFF09A
1:  move.w  %d1,0xDFF180
    bra.s   1b

super:                          | supervisor mode, d6 = source, d7 = length
    move.w  #0x2700,%sr
    lea     0x400.w,%sp
    move.w  #0x7FFF,0xDFF09A    | INTENA off
    move.w  #0x7FFF,0xDFF09C    | INTREQ clear
    move.b  0xDFF002,%d0        | DMACONR: dummy read (BBUSY quirk)
2:  btst    #6,0xDFF002         | wait for Blitter idle (BBUSY, bit 14)
    bne.s   2b
    move.w  #0x7FFF,0xDFF096    | all DMA off
    move.w  #0x7FFF,0xDFF09C
    .ifdef CACHE040
    cpusha  %bc                 | push dirty OS data before disabling 040 caches
    moveq   #0,%d0
    .else
    move.l  #0x0808,%d0         | 020/030 clear and disable
    .endif
    movec   %d0,%cacr
    .ifdef CACHE060
    | Older Kickstart identifies a 060 as a 040. Probe PCR with a temporary
    | illegal-instruction vector after caches are disabled, then restore it.
    movec   %vbr,%d0
    move.l  %d0,%a0
    move.l  16(%a0),%a2
    lea     pcr_unavailable(%pc),%a1
    move.l  %a1,16(%a0)
    moveq   #-1,%d0
    movec   %pcr,%d0
    move.l  %a2,16(%a0)
    cmpi.l  #-1,%d0
    bne.s   pcr_present
    move.w  #0x00FF,%d1
    bra     fail
pcr_unavailable:
    addq.l  #4,2(%sp)
    rte
pcr_present:
    .endif
    lea     reloc(%pc),%a0      | install relocator at RELOC_ADDR
    lea     RELOC_ADDR.w,%a1
    moveq   #(reloc_end-reloc)/2-1,%d0
3:  move.w  (%a0)+,(%a1)+
    dbra    %d0,3b
    move.l  %d6,%a0             | src = staging
    .ifdef RELOCATE
    move.l  %a3,%a1             | allocated destination
    .else
    lea     PAYLOAD_BASE,%a1    | dst
    .endif
    move.l  %d7,%d0
    lsr.l   #2,%d0              | longwords
    jmp     RELOC_ADDR.w

reloc:                          | position independent
    cmp.l   %a0,%a1
    bhi.s   2f                  | dst > src: copy descending
1:  move.l  (%a0)+,(%a1)+
    subq.l  #1,%d0
    bne.s   1b
    .ifdef RELOCATE
    bra.s   fix_addresses
    .else
    jmp     PAYLOAD_BASE
    .endif
2:  lea     0(%a0,%d7.l),%a0    | end of src
    lea     0(%a1,%d7.l),%a1    | end of dst
3:  move.l  -(%a0),-(%a1)
    subq.l  #1,%d0
    bne.s   3b
    .ifdef RELOCATE
fix_addresses:
    lea     (%a3,%d3.l),%a0
    move.l  %a3,%d1
    sub.l   %d4,%d1            | actual base minus link base
4:  tst.l   %d2
    beq.s   7f
    move.l  (%a0)+,%d0
    bmi.s   5f
    add.l   %d1,(%a3,%d0.l)
    bra.s   6f
5:  andi.l  #0x7FFFFFFF,%d0
    sub.l   %d1,(%a3,%d0.l)
6:  subq.l  #1,%d2
    bra.s   4b
7:  jmp     (%a3)
    .else
    jmp     PAYLOAD_BASE
    .endif
reloc_end:
