.section .text.start
.global _start
_start:
 jsr -120(%a6) /* Exec.Disable is valid from the boot task user mode */
 move.l #0x7fff0,%sp
 lea __bss_start,%a0
 lea __bss_end,%a1
1: cmp.l %a1,%a0
 bhs 2f
 clr.l (%a0)+
 bra 1b
2: jsr game_main
 bra 2b
.section .rodata
.global field
.balign 4
field: .incbin "build/little-league/field.bin"
