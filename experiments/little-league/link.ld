ENTRY(_start)
SECTIONS {
 . = 0x40000;
 .text : { *(.text.start) *(.text*) }
 .rodata : { *(.rodata*) }
 .data : { *(.data*) }
 . = ALIGN(4);
 __bss_start = .;
 .bss : { *(.bss*) *(COMMON) }
 . = ALIGN(4);
 __bss_end = .;
 ASSERT(__bss_end < 0x7c000, "Payload overlaps stack")
}
