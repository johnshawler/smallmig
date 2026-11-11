#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT="$HERE/root"
export PATH="$ROOT/usr/bin:$PATH"
export LD_LIBRARY_PATH="$ROOT/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
mkdir -p "$HERE/smoke"
cat > "$HERE/smoke/smoke.c" <<'C'
#include <stdio.h>
extern int m68k_probe(void);
int main(void) {
    int answer = m68k_probe();
    printf("m68020 smoke: %d\n", answer);
    return answer != 42;
}
C
cat > "$HERE/smoke/probe.s" <<'ASM'
    .text
    .globl m68k_probe
    .type m68k_probe,@function
m68k_probe:
    moveq #42,%d0
    rts
    .size m68k_probe,.-m68k_probe
    .section .note.GNU-stack,"",@progbits
ASM
m68k-linux-gnu-gcc --version | head -1
m68k-linux-gnu-as --version | head -1
m68k-linux-gnu-ld --version | head -1
m68k-linux-gnu-nm --version | head -1
m68k-linux-gnu-objcopy --version | head -1
qemu-m68k --version | head -1
m68k-linux-gnu-as -m68020 "$HERE/smoke/probe.s" -o "$HERE/smoke/probe.o"
m68k-linux-gnu-ld -r "$HERE/smoke/probe.o" -o "$HERE/smoke/probe-linked.o"
m68k-linux-gnu-nm "$HERE/smoke/probe-linked.o"
m68k-linux-gnu-objcopy -O binary -j .text "$HERE/smoke/probe-linked.o" "$HERE/smoke/probe.bin"
m68k-linux-gnu-gcc -static -m68020 -O1 "$HERE/smoke/smoke.c" "$HERE/smoke/probe.o" -o "$HERE/smoke/static-no-sysroot"
qemu-m68k -cpu m68020 -one-insn-per-tb "$HERE/smoke/static-no-sysroot"
m68k-linux-gnu-gcc --sysroot="$ROOT" -static -m68020 -O1 "$HERE/smoke/smoke.c" "$HERE/smoke/probe.o" -o "$HERE/smoke/static-sysroot"
qemu-m68k -cpu m68020 -one-insn-per-tb "$HERE/smoke/static-sysroot"
m68k-linux-gnu-gcc --sysroot="$ROOT" -m68020 -O1 "$HERE/smoke/smoke.c" "$HERE/smoke/probe.o" -o "$HERE/smoke/dynamic-sysroot"
qemu-m68k -cpu m68020 -one-insn-per-tb -L "$ROOT/usr/m68k-linux-gnu" "$HERE/smoke/dynamic-sysroot"
printf '%s\n' 'PASS: assembler, linker, nm, objcopy, static C and dynamic C on qemu m68020.'
