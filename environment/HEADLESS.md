# Headless cloud execution

The `Headless emulators` GitHub Actions workflow starts a Debian 13 x86_64
container, installs Mesen and FS-UAE, and executes both without a physical display.
Each run is bounded and the container is discarded afterward; this is repeatable
cloud testing rather than a persistent server.

The installation/execution run [42377954243](https://github.com/johnshawler/smallmig/actions/runs/42377954243)
passed on 7 November 2026:

- Official Mesen 2.1.1 test runner: 240 frames, with exactly 120 NMI increments
  across the final 120 frames.
- FS-UAE 3.1.66-2+b1 under Xvfb/software Mesa: original native 68020 test firmware
  completed five PAL frame loops. A1200, AGA, 68EC020, 2 MiB Chip and 8 MiB Fast;
  stock CPU timing and JIT disabled.

The Mesen download is SHA-256 pinned by `tools/setup_mesen.py`. Package versions
are recorded by each installation. FS-UAE's Debian build disables its unfinished
Lua interface, so native firmware reports through the emulator's supported
diagnostic memory-write log. It executes real instructions rather than treating
an emulator process that remains alive as a successful test.

In a Debian 13 x86_64 container or private cloud shell, run:

```sh
sh environment/headless-install.sh
python3 environment/headless-smoke.py
python3 environment/headless-aga.py
```

Installation needs root inside that container. Mesen uses its headless test-runner
mode; FS-UAE 3.x uses a virtual X display with software rendering. The AGA check
executes the actual Copper builder, captures its native framebuffer, and compares
all 61,440 pixels with the synthetic reference. Both 16-bit and experimental
32-bit paths passed in [run 42381806277](https://github.com/johnshawler/smallmig/actions/runs/42381806277),
including all 32 fine-scroll phases, wrapping, exact layers, blanking, sprites,
palette changes and the PAL Copper line-counter wrap.

The same run copied an original 68020 write loop to configured Zorro II Fast RAM
and timed 4,096 longword writes into Chip RAM with the display active. The minimum
of three trials, each beginning at the visible raster start, was 5,712 E-clock
ticks for 16-bit fetches and 2,979 ticks for 32-bit fetches (about 48% less time).
This measures display bus contention, not full-game speed. Repeated runs delete
previous screenshots before capture to prevent accepting stale output.

A second job executes 1,131 original translator fixtures under QEMU's 68020 core:
36,192 runs with zero failures, comparing registers, flags, memory and individual
I/O access cycles. Debian QEMU 10 uses `-one-insn-per-tb` for the reference run;
older QEMU releases called this option `-singlestep`.

Public jobs only generate original fixtures and original test firmware. They do
not upload or download Little League cartridge bytes, decoded art, game ADFs or
licensed Kickstart. Private full-game tests require a private runner with those
inputs mounted separately. Installation checks and synthetic renderer comparisons
do not certify full-game speed.
