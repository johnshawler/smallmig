# Little League Baseball original-engine port

This development path runs the original cartridge program through the 6502-to-68020 translator and runtime. It replaces the simplified batting prototype as the basis for the full port. Menus, team selection, batting, pitching, fielding and game rules come from the original program.

**The 1:1 acceptance goal is still open.** The full game boots and reaches live play, but the latest native speed is far below real time on the declared A1200. This is not a finished release.

## Build

From the Small Mig root, with Python 3 and m68k GCC/binutils installed:

```sh
python3 ports/little-league/build.py --rom /private/little-league.nes --kickstart /private/A1200.rom
```

The default player image is `build/little-league-original/Little-League-Original-Exact.adf`. Open the generated `Little-League.fs-uae` profile in FS-UAE. The target remains PAL A1200, stock 68EC020, AGA, 2 MiB Chip and 8 MiB Fast. No JIT, accelerated CPU or extra RAM is requested.

The default sound path renders the original APU events to Paula PCM. `--cue-audio` selects the older, faster, approximate sound mode for diagnosis; it is not the fidelity target. Exact sound cannot play continuously while the game runs below real time.

The wrapper accepts only the verified cartridge SHA-256 `f33ee3c2cdf4cb23bb060574234fa6ebb45ac0c7dea1f910d1b86c0e42990c23`. Cartridge bytes, decoded game assets, ADFs and Kickstart remain local.

Controls in the supplied profile: arrows = direction, right Ctrl = NES A, X = NES B, Return = Start, Space = Select. A physical Amiga uses joystick port 2 with its second button plus the keyboard Start/Select keys. Controller behavior during all game situations still needs full acceptance testing.

## Verification

```sh
python3 ports/little-league/check.py --rom /private/little-league.nes
python3 ports/little-league/check.py --rom /private/little-league.nes --draw-every 4
python3 ports/little-league/check.py --rom /private/little-league.nes --mesen /Applications/Mesen.app/Contents/MacOS/Mesen
```

These compare the fast PPU against its per-dot reference and the planar output against reference pixels. They also run the existing APU tests. They exercise the Watch Game script and eight coverage scripts, 6,000 frames each. The optional `--mesen` run separately compares all 2,048 bytes of game RAM at completed frames 1,500 and 6,000 against the installed Mesen. It is not a complete external instruction trace or native-speed certification.

`vendor/` preserves the existing full-engine source and its documentation. Historical measurements in those documents are explicitly historical; current acceptance evidence belongs in `VALIDATION.md`. Provenance is pinned in `UPSTREAM.json`. No new blanket license is assigned to imported source.

## Remaining acceptance work

- Original speed, continuous exact sound and responsive controls on the declared Amiga.
- Fresh external reference comparison, native graphics checks and controller-driven gameplay.
- Complete matches, inning changes, scoring, results and restart, including two-player input.
- Reproducible release ADF with clear build identity and private cartridge handling.
