# Source this file from bash: source /absolute/path/to/amiga-recovery-m68k/activate.sh
AMIGA_M68K_TOOLCHAIN=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export AMIGA_M68K_TOOLCHAIN
export PATH="$AMIGA_M68K_TOOLCHAIN/root/usr/bin:$PATH"
export LD_LIBRARY_PATH="$AMIGA_M68K_TOOLCHAIN/root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
