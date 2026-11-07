# Small Mig

Reusable NES/6502-to-Amiga development harness. Provisional target: PAL A1200, 68EC020, AGA, 2 MiB Chip RAM and 8 MiB Fast RAM. This repository is source preparation, **not a published Codex environment or a full-game converter**.

## Contents

- `src/boot.s`, `build.py`, `run.py`: original native graphics/input/Paula smoke fixture.
- `experiments/6502-probe/`: original bounded movement/collision/score translation probe with its 0BSD license.
- `experiments/homebrew/`: selected Falling v1.1 movement translation, host model, source-reference runner and native checks. It implements a limited slice, not the complete game.
- `tools/`: pinned host-tool download scripts and notices. Runtime executables are not bundled.
- `environment/`: setup/startup scripts and optional local container-isolation preparation.

## Setup and build

The supplied tool pins target Debian 13 Linux x86_64. From the repository root:

```sh
python3 tools/setup.py
python3 build.py
AMIGA_KICKSTART=/private/path/to/A1200-Kickstart-3.1.rom python3 run.py
```

Runtime shared libraries must be installed. The optional `environment/setup.py` installs Mesen and performs full readiness checks, which additionally require the separately supplied licensed Falling fixture described below. A root setup runner on Debian 13 may add `--install-runtime`; inspect the pinned package lock first. All downloads remain subject to your environment's configured network access.

Cursor keys move the original smoke fixture; right Ctrl requests a Paula tone. It takes over the emulated machine and does not return to Workbench. Exit or reset the emulator to stop.

Optional checks require the pinned Falling NES fixture and matching CHR file supplied locally at `experiments/homebrew/references/falling/falling.nes` and `experiments/homebrew/references/falling/source/falling.chr`. These binary fixture files are **not included in this repository**. Their pinned upstream location, hash and license are documented in `experiments/homebrew/README.md`. Mesen is installed separately with `python3 tools/setup_mesen.py`.

Optional checks:

```sh
python3 experiments/6502-probe/run_test.py
python3 experiments/homebrew/run_mesen_reference.py
python3 experiments/homebrew/run_test.py --with-mesen
python3 environment/startup_check.py --emulators
```

Supply a lawfully obtained private A1200 Kickstart before native tests. No proprietary firmware is included. Per-run emulators and profiles are isolated by the harness; physical-hardware behavior and full-game performance are unverified.

## Provenance and validation

Imported from the existing Small Mig source delivery dated 2026-11-03. That development workspace reported 240 Mesen frames / 180 observed movement calls and 372 native cases / 5,580 result bytes, plus graphics/input/audio and two local-container isolation checks. Those are historical development results, **not fresh validation of this repository or Codex cloud-task isolation**. Raw workspace logs, generated disks, runtime binaries and private ROMs were intentionally excluded.

The public import receives Python syntax checks and local host-only fixture checks where dependencies permit. See `PUBLICATION.md` for exact results and limits.

## Licenses

Existing file-specific licenses are preserved; no new blanket license is assigned to the whole repository. The original probes/adapters carry 0BSD notices. The pinned Falling source and external fixture are MIT-licensed, Copyright (c) 2018 tragicmuffin, with notices in `experiments/homebrew/LICENSE_FALLING_MIT` and its `references/falling/LICENSE`. They come from [xram64/falling-nes](https://github.com/xram64/falling-nes/tree/52dcb8a951200562e696dfc2aba5d4d14edd0078). No NES ROM, CHR binary or proprietary firmware is bundled. The optional homebrew tests require separately supplied local fixture files. Mesen's GPL-3.0 notice is retained; its executable is downloaded separately from its pinned official release. References with unclear redistribution rights are not bundled.


## Little League Baseball batting prototype

The new [Little League experiment](experiments/little-league/README.md) builds a native Amiga batting loop from a separately supplied USA cartridge. It captures the original batting view in Mesen and reconstructs its background and players from mapped CHR, nametables, palettes and OAM. Gameplay and Paula effects in this first slice are newly implemented. The original NES game engine, fielding and music have not been ported.

The original smoke-demo build and launcher now also recognize installed macOS `m68k-elf-*` tools and FS-UAE. The new experiment additionally requires an m68k GCC cross compiler.

## Little League Baseball original engine

The [full-game port](ports/little-league/README.md) now uses the original cartridge program through the existing static translator, PPU/MMC1 runtime, planar renderer and APU mixer. It builds a private bootable ADF. The earlier batting prototype is retained as an experiment. Full-speed 1:1 acceptance on the declared A1200 remains open.
