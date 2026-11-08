# Little League Baseball: first native batting section

This is an initial playable Amiga prototype using graphics from the supplied Little League Baseball: Championship Series USA cartridge. It does not execute or translate the NES game engine. It is separate from earlier Little League port projects.

## What works

- Native 68020 code and a bootable ADF using Small Mig's loader approach.
- The original batting background, pitcher idle/throw poses and batter, reconstructed from a live Mesen PPU/OAM capture.
- Variable-speed CPU pitches, batter movement, one swing per pitch, a contact window, ball flight, singles/doubles/home runs, balls/strikes, walks, strikeouts, base occupancy and a three-out inning reset.
- Generated Paula effects for swings, contact and results. These are placeholder effects; listening/PCM acceptance and the original game's music are pending.
- Double-buffered four-plane display, blitter background copies, packed masked sprite rows and packed glyph drawing. HUD backdrops are baked at build time.

This is a batting-practice loop. Fielding, CPU defense, baserunning controls, side changes, team selection, original simulation timing, original swing animation and a full match remain to be implemented. The lower NES stat panels are static reference artwork; the top Small Mig strip contains the live prototype counts. No sustained frame-rate or real-hardware claim is made.

## Target and inputs

The local profile is PAL A1200, stock 68EC020, AGA, 2 MiB Chip and **zero Fast RAM**. The loader reserves 256 KiB Chip at `0x40000`, including its private stack. It fails instead of overwriting occupied memory. This fixed-address bare-metal prototype takes over the machine; reset or quit FS-UAE to stop.

Supply the USA cartridge privately. Its verified identity is:

- 262,160 bytes; NES 2.0 / MMC1 mapper 1.
- 128 KiB PRG and 128 KiB CHR.
- SHA-256 `f33ee3c2cdf4cb23bb060574234fa6ebb45ac0c7dea1f910d1b86c0e42990c23`.

Mesen, FS-UAE, an m68k GCC/binutils cross toolchain and Python 3 are required. Tested locally with the installed macOS ARM64 tools, m68k GCC 16.2.0 and FS-UAE 3.2.35. Mesen runs via its test-runner interface. No runtime executables, cartridge, decoded assets or Kickstart are committed.

## Build and play

From the repository root:

```sh
python3 build.py
AMIGA_KICKSTART=/private/A1200.rom python3 run.py

python3 experiments/little-league/build.py --rom /private/little-league.nes
python3 experiments/little-league/run.py --kickstart /private/A1200.rom
```

The first experiment build runs Mesen for 3,600 source frames. Use `--mesen /path/to/Mesen` if it is not on PATH or in `/Applications/Mesen.app`. GCC/binutils may use the `m68k-elf-` or `m68k-linux-gnu-` prefix. `--refresh-reference` regenerates the capture. All generated assets and evidence stay under `build/little-league/`.

The player image is `build/little-league/Little-League-SmallMig-Batting.adf`. Boot it with the declared A1200 profile and your Kickstart. The generated `Batting.fs-uae` also maps Space to joystick fire. Use `--write-config` to generate the profile without launching; opening that profile in FS-UAE is another launch route.

- Left/right: move the batter. Direction held at swing time influences hit direction.
- Space, right Ctrl, or joystick fire: swing. Fire during the short ready/result pause starts the next pitch sooner.
- Pitches otherwise start automatically. Time the swing slightly before the ball reaches home plate.

Space is a host mapping in the supplied FS-UAE profile; a physical Amiga uses its joystick fire button.

## Checks and limits

```sh
cc -O2 -Wno-pointer-to-int-cast -I build/little-league \
  experiments/little-league/test_game.c -o build/little-league/test-game
build/little-league/test-game
```

The host checks exercise takes, strikeouts, forced walks, 13 contact timings, home-run scoring, held-fire behavior, movement limits and inning reset. They verify the new prototype rules, not equivalence with the original NES game.

For a separate native integration playback:

```sh
python3 experiments/little-league/build.py --rom /private/little-league.nes --replay
```

This writes `Little-League-SmallMig-Replay.adf`; the player ADF is retained. The playback feeds deterministic controller inputs through the same update/render path. Rebuild without `--replay` before inspecting the player ELF/disassembly, which are shared build intermediates.

Native verification observed the original smoke-demo sprite boot and movement, then the batting prototype boot, movement and input. The optimized native replay visibly advanced to two hits and two runs and continued pitching in FS-UAE with zero Fast RAM. Sound implementation exists, but physical listening and captured PCM have not been accepted. Sustained cadence, all outcome paths on target and physical hardware are unverified.

The source-frame reconstruction matched 61,411/61,440 RGB pixels before Amiga 12-bit palette conversion and HUD changes. This is one batting frame, not an all-scenes fidelity result. `source-graphics-report.json`, `source/reference-report.json` and the build reports retain the exact scope and hashes.

The boot block's additive checksum, payload limit, disk size and linker memory bounds are checked at build time. Palette writes are unrolled to avoid an observed m68k GCC 16 source/destination postincrement problem. No licensed or proprietary game data is embedded in these source files; builds derive graphics locally from the privately supplied cartridge.
