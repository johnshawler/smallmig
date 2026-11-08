/* Fast-required A1200 layout. CPU code, ROM data, BSS and stack use Fast RAM;
 * custom-chip output uses .chipbuf. The relocation loader requests MEMF_FAST
 * and applies fixups at the actual allocation, so ORIGIN(fast) is a link base,
 * not a promise that this address is available at runtime. See memory_map.py.
 */
OUTPUT_FORMAT("elf32-m68k")
OUTPUT_ARCH(m68k)
/* FAST RAM variant (tools/build_adf.sh, FASTRAM=1 default): the program is linked at 0x200000 (the 8 MB fast RAM of the machine: 0x200000-0x9FFFFF), only what the custom chips
 * access lives in chip RAM: the bitplane buffers, the Copper list, the sprite and the Paula sample buffers (all in the section .chipbuf, linked at 0x1000).  The bootblock / loader
 * stage the payload in chip RAM and the relocator copies it to 0x200000. */
MEMORY
{
    chip (rwx) : ORIGIN = 0x1000,   LENGTH = 0x1EF000
    fast (rwx) : ORIGIN = DEFINED(FAST_BASE) ? FAST_BASE : 0x200000, LENGTH = 0x800000
}
ENTRY(_start)
PROVIDE(_chip_limit = 0x200000);
PROVIDE(_stack_size = 0x4000);
SECTIONS
{
    . = ORIGIN(fast);
    _payload_base = .;
    .text : {
        KEEP(*(.text.start))
        _pr0 = .;  *code.o(.text .text.*)                                   /* translated 6502 code */
        _pr1 = .;  *rt_x_s.o(.text .text.*)                                 /* assembler glue: dispatch, helper entry */
        _pr2 = .;  *rt_x.o(.text .text.*)                                   /* C helpers: I/O access, cycle limit, slow path, wait-loop skipping */
        _pr3 = .;  *rt_core.o(.text .text.*)                                /* time model, PPU register access, NMI logic */
        _pr4 = .;  *ppu_ref.o(.text .text.*)                                /* PPU: line renderer, per-dot model */
        _pr5 = .;  *cpu6502.o(.text .text.*) *mapper_mmc1.o(.text .text.*)  /* interpreter (slow path), mapper */
        _pr6 = .;  *apu.o(.text .text.*)                                    /* APU */
        _pr7 = .;  *arender.o(.text .text.*)                                 /* planar renderer (runtime/arender.c) */
        _pr8 = .;  *c2p.o(.text .text.*) *display.o(.text .text.*) *display_ar.o(.text .text.*) *display_ar2.o(.text .text.*) *main.o(.text .text.*) *audio.o(.text .text.*) *platform.o(.text .text.*) *telem.o(.text .text.*) *crt0.o(.text .text.*) *isr.o(.text .text.*) *libc.o(.text .text.*) *tabs.o(.text .text.*)
        _idle0 = .; *(.text.idle) _idle1 = .;                               /* STOP loop of the pacing wait */
        _pr9 = .;  *(.text .text.*)                                         /* libgcc (64-bit division) and the rest */
        _pr10 = .;
        *(.rodata .rodata.*)
    } > fast
    .data : ALIGN(4) { *(.data .data.*) . = ALIGN(4); } > fast
    .rom : ALIGN(4) { rom_start = .; *(.rom) . = ALIGN(4); } > fast
    _load_end = .;
    .bss (NOLOAD) : ALIGN(16) {
        _bss_start = .;
        *(.bss .bss.* COMMON)
        . = ALIGN(4);
        _bss_end = .;
    } > fast
    .stack (NOLOAD) : ALIGN(4) { . += _stack_size; _stack_top = .; } > fast
    _end = .;
    ASSERT(_end <= ORIGIN(fast)+LENGTH(fast), "image does not fit into the 8 MB of fast RAM")
    .chipbuf (NOLOAD) : ALIGN(16) { _chip_start = .; *(.chipbuf) . = ALIGN(4); _chip_end = .; } > chip
    ASSERT(_chip_end <= 0x1F0000, "chip RAM buffers too large")
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
