# Little League Baseball original-engine port

This path runs the original cartridge program through the 6502-to-68020 translator, MMC1/PPU runtime, planar renderer and original APU mixer. It includes the original menus, teams, batting, pitching, fielding, rules and complete games. The earlier batting experiment remains separate.

The native translated game has completed the reference full match and passed all 11 RAM checkpoints through 100,000 frames. Fresh native menu, batting and field screenshots match the reference pixels. See `VALIDATION.md` for exact results and their scope.

## Build and play

With Python 3 and m68k GCC/binutils installed, run from the Small Mig root:

```sh
python3 ports/little-league/build.py --rom /private/little-league.nes --kickstart /private/A1200.rom
```

Open `build/little-league-original/Little-League.fs-uae` in FS-UAE. The player image is `Little-League-Original-Exact.adf`. The loader allocates and relocates into available Fast RAM; it no longer requires one fixed memory address.

Click inside the game window if the controller does not respond. Choose Exhibition, 1P and the two teams with Z. On the lineup screen, X leaves order editing; press Right until the bottom command says End, then Z to begin the inning.

Use AGA, a 68020/68030, 2 MiB Chip and at least 4 MiB Fast RAM. The generated NTSC profile uses FS-UAE fast CPU mode with JIT disabled. This is the real-time playtest configuration, not a claim of stock 14 MHz A1200 speed. Stock-speed hardware acceptance remains open; the earlier stock exact-audio measurement was about 34% speed. Physical-hardware performance has not been certified.

`--standard pal` writes a PAL profile. `--stock-timing` selects a hardware-speed diagnostic profile. `--cue-audio` selects the older approximate sound path for diagnosis; exact original APU PCM is the default.

Controls in the supplied profile:

- Arrows: original controller directions.
- Z or right Ctrl: NES A.
- X: NES B.
- Return: Start.
- Space: Select.

Add `--two-player` when generating the profile to enable a second keyboard controller: WASD directions, F for A, G for B. Choose 2P in the original Exhibition menu. Both controller ports, batter movement, pitching and a timed human swing producing a hit were exercised in this configuration.

Physical hardware uses joystick port 2 with its second button, plus keyboard Start/Select. Reset or quit the emulator to leave the game.

Only the verified USA cartridge is accepted: SHA-256 `f33ee3c2cdf4cb23bb060574234fa6ebb45ac0c7dea1f910d1b86c0e42990c23`. Cartridge bytes, generated game assets, ADFs and Kickstart remain private and are excluded from public source.

## Reference checks

```sh
python3 ports/little-league/check.py --rom /private/little-league.nes
python3 ports/little-league/check.py --rom /private/little-league.nes --draw-every 4
python3 ports/little-league/check.py --rom /private/little-league.nes --mesen /Applications/Mesen.app/Contents/MacOS/Mesen
```

The checks compare the fast PPU and planar output against the per-dot reference, run the existing APU tests, and optionally compare all 2,048 game RAM bytes with a fresh Mesen run. Native screenshot comparison and complete-match RAM checks are separate tests. The internal checks do not certify native speed.

`vendor/` preserves the pinned existing full-engine source, with local build/runtime changes listed in `UPSTREAM.json`. Documentation under `vendor/docs/` contains historical upstream results; current evidence is recorded in `VALIDATION.md`. Imported patch whitespace and existing notices are preserved. No new blanket license is assigned.
