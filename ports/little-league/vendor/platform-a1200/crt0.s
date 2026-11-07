| crt0.s - payload entry (A1200).  Linked first (section .text.start) at 0x800.
| Entered from the bootblock relocator in SUPERVISOR mode with interrupts masked, or via plat_restart().  Never returns.
| Uses nothing from the OS.  68020: VBR := 0 (the vectors are installed at chip address 0), caches: instruction cache cleared and
| enabled, data cache (68030) off - the custom chips/CIAs must never be cached.
    .section .text.start,"ax"
    .globl  _start
_start:
    move.w  #0x2700,%sr             | supervisor, all interrupts masked
    moveq   #0,%d0
    movec   %d0,%vbr
    .ifdef CACHE040
    | Full 68040 build, flat physical addressing. Low 16 MB data is serialized
    | and uncached for Chip RAM / DMA / hardware. The selected high Fast RAM
    | block is private to the CPU and can use copyback caching.
    movec   %d0,%tc
    movec   %d0,%itt0
    movec   %d0,%itt1
    move.l  #0x0000C040,%d0
    movec   %d0,%dtt0
    move.l  #_payload_base,%d0
    andi.l  #0xFF000000,%d0
    beq.s   cache_high_done
    ori.l   #0xC020,%d0
cache_high_done:
    movec   %d0,%dtt1
    cinva   %bc
    .ifdef CACHE060
    | MC68060 UM: retain PCR settings, enable superscalar
    | dispatch, clear/enable branch cache, and enable the store buffer. The
    | low-memory DTT0 serialized mode bypasses that buffer for hardware.
    movec   %pcr,%d0
    ori.l   #1,%d0
    movec   %d0,%pcr
    move.l  #0xA0C08000,%d0
    .else
    move.l  #0x80008000,%d0
    .endif
    .else
    .ifdef CACHE030
    | Full 68030 only. TT0 covers data accesses in the first 16 MB, including
    | Chip RAM and all custom/CIA registers, with caching inhibited. Fast RAM
    | above that region can use the write-through data cache. TT registers
    | operate even with TC.E=0 (MC68030 User Manual section 9.7.3).
    | TT0: E|CI|RWM|FC-base(data=1)|FC-mask(ignore supervisor bit=4).
    lea     cache030_config(%pc),%a0
    pmove   (%a0),%tc
    pmove   (%a0),%tt1
    pmove   4(%a0),%tt0
    move.l  #0x0919,%d0             | clear I/D, enable I/D, instruction burst only
    .else
    move.l  #0x0809,%d0             | clear I/D, enable I only
    .endif
    .endif
    movec   %d0,%cacr
    lea     _stack_top,%sp
    jsr     plat_hw_reset           | quiesce all chips (no BSS use before here)
    | zero .bss
    lea     _bss_start,%a0
    lea     _bss_end,%a1
1:  cmp.l   %a0,%a1
    bls.s   2f
    clr.l   (%a0)+
    bra.s   1b
2:
    lea     _chip_start,%a0         | clear the chip RAM variables (Copper list, sprite/audio buffers: DMA-visible, must start zeroed)
    lea     _chip_end,%a1
5:  cmp.l   %a0,%a1
    bls.s   6f
    clr.l   (%a0)+
    bra.s   5b
6:
    | install the 64 exception vectors at 0x000000 (chip RAM; OVL is 0)
    lea     plat_vectors,%a0
    sub.l   %a1,%a1
    moveq   #63,%d0
3:  move.l  (%a0)+,(%a1)+
    dbra    %d0,3b
    jsr     plat_init               | detect standard, display, CIA, IRQs
    jsr     main
4:  bra.s   4b                      | main() returned: idle forever
    .ifdef CACHE030
    .even
cache030_config:
    .long 0,0x00008514
    .endif
