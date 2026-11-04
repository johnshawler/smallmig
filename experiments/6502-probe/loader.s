/* SPDX-License-Identifier: 0BSD. OS boot entry -> read a separate 16 KiB payload. */
.section .text
.global _start
_start:
    .ascii "DOS\0"
    .long 0,880
    move.l %a1,%a5          /* boot device IOStdReq */
    moveq #2,%d1           /* live free Chip bytes before allocation */
    jsr -216(%a6)           /* exec.AvailMem */
    move.l %d0,%a2
    moveq #4,%d1           /* live free Fast bytes before allocation */
    jsr -216(%a6)
    move.l %d0,%a3
    move.l #32768,%d0
    move.l #0x10002,%d1     /* Chip | Clear */
    jsr -198(%a6)
    tst.l %d0
    beq failed
    move.l %d0,%a4
    move.l %a2,32000(%a4)
    move.l %a3,32004(%a4)
    moveq #2,%d1
    jsr -216(%a6)
    move.l %d0,32008(%a4)
    moveq #4,%d1
    jsr -216(%a6)
    move.l %d0,32012(%a4)
    move.w #2,28(%a5)      /* CMD_READ */
    move.l #16384,36(%a5)  /* io_Length */
    move.l %a4,40(%a5)     /* io_Data */
    move.l #1024,44(%a5)   /* io_Offset */
    move.l %a5,%a1
    jsr -456(%a6)          /* exec.DoIO */
    tst.l %d0
    bne failed
    move.l %a4,%a0
    jmp (%a4)             /* payload A0=allocation base, A6=Exec */
failed:
    moveq #-1,%d0
    rts
