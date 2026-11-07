/* Small Mig boot protocol: load native payload, then take over the machine. */
.section .text
.global _start
_start:
 .ascii "DOS\0"
 .long 0,880
 move.l %a1,%a5
 move.l #262144,%d0
 move.l #0x40000,%a1
 jsr -204(%a6) /* AllocAbs: fail rather than overwrite occupied memory */
 tst.l %d0
 beq failed
 move.w #2,28(%a5)
 move.l #65536,36(%a5)
 move.l #0x40000,40(%a5)
 move.l #1024,44(%a5)
 move.l %a5,%a1
 jsr -456(%a6)
 tst.l %d0
 bne failed
 jmp 0x40000
failed:
 moveq #-1,%d0
 rts
