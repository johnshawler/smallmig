# Little League Baseball original-engine port

This path runs the original cartridge program through the 6502-to-68020 translator, MMC1/PPU runtime, planar renderer and original APU mixer. It includes the original menus, teams, batting, pitching, fielding, rules and complete games. The earlier batting experiment remains separate.

The native translated game has completed the reference full match and passed all 11 RAM checkpoints through 100,000 frames. Fresh native menu, batting and field screenshots match the reference pixels. See `VALIDATION.md` for exact results and their scope.

The current timing contract preserves the USA cartridge's **60.0988 Hz source
updates, input and sound**, with PAL presentation scheduled separately near
50 Hz. The supplied optimization brief supersedes the earlier proposal to convert
logic to 50 Hz. `SPEED.md` records the source measurements and cost attribution.

## Build and play

With Python 3 and m68k GCC/binutils installed, run from the Small Mig root:

```sh
python3 ports/little-league/build.py --rom /private/little-league.nes --kickstart /private/A1200.rom
```

Open `build/little-league-original/Little-League.fs-uae` in FS-UAE. The player image is `Little-League-Original-Exact.adf`. The loader allocates and relocates into available Fast RAM; it no longer requires one fixed memory address.

Click inside the game window if the controller does not respond. Choose Exhibition, 1P and the two teams with Z. On the lineup screen, X leaves order editing; press Right until the bottom command says End, then Z to begin the inning.

Use AGA, a 68020/68030, 2 MiB Chip and at least 4 MiB Fast RAM. The generated profile now defaults to stock PAL 68EC020 timing, 2 MiB Chip and 8 MiB Fast RAM, with JIT disabled. `--fast-cpu` explicitly selects an accelerated playtest. Full-speed stock-hardware acceptance remains open. Stock-speed hardware acceptance remains open; the earlier stock exact-audio measurement was about 34% speed. Physical-hardware performance has not been certified.

`--wide-dma` builds a separate experimental `Little-League-Original-Exact-Wide.adf`
using 32-bit AGA fetches. It passed the cloud pixel fixture, nine graphics coverage
scripts and a 100,001-frame native state check. The synthetic Chip RAM write test
was about 48% faster with wider fetches; full-game stock-speed acceptance is still
open. The default build retains the existing renderer.

`--standard ntsc` selects NTSC presentation without changing the source clock. `--stock-timing` explicitly selects the default hardware-speed profile. `--cue-audio` selects the older approximate sound path for diagnosis; exact original APU PCM is the default.

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
python3 ports/little-league/check.py --rom /private/little-league.nes --wide-dma
python3 ports/little-league/check.py --rom /private/little-league.nes --wide-dma --compact-rowkey --force-row-rebuild
python3 ports/little-league/check.py --rom /private/little-league.nes --mesen /Applications/Mesen.app/Contents/MacOS/Mesen
```

The checks compare the fast PPU and planar output against the per-dot reference, run the existing APU tests, and optionally compare all 2,048 game RAM bytes with a fresh Mesen run. Native screenshot comparison and complete-match RAM checks are separate tests. The internal checks do not certify native speed.

`vendor/` preserves the pinned existing full-engine source, with local build/runtime changes listed in `UPSTREAM.json`. Documentation under `vendor/docs/` contains historical upstream results; current evidence is recorded in `VALIDATION.md`. Imported patch whitespace and existing notices are preserved. No new blanket license is assigned.

The candidate `--compact-rowkey` path compares exact meaningful sprite-row inputs
without clearing or checking unused slots. It retains the original key path and
supports forced rebuild checks. It remains opt-in pending complete player timing.
Each build exports `memory-map.json` and `memory-map.md`; their addresses are
linked addresses unless a running relocated base was supplied to `memory_map.py`.

## November 10 source recovery

See [recovery results](RECOVERY-2026-11-10.md) for the reproducible older-source build, assembler compatibility fix, fresh bounded tests and remaining limits. This does not restore later workspace-only native conversions.

## Recovered memory-reduction candidate (November 11)

`--external-renderer-storage` omits the unused fallback renderer allocation only in the native stage-2b player. Candidate files stay under `build/little-league-external-storage/`; baseline files remain unchanged. Exact Fast reservation drops from 2,755,032 to 1,784,144 bytes, while Chip reservation remains 1,043,848 bytes. A separately configured PAL A1200 test with 2 MiB Fast reaches on-field gameplay after 9,000 fields. The generated profile conservatively remains 8 MiB Fast. This is not zero-Fast stock or full-speed acceptance.

Guarded host rendering passes 107,982 picture comparisons across nine scripts and both buffer sets. Native baseline/candidate state streams are identical for 6,000 frames and PCM matches the host. Both builds still fail the host state oracle on four pre-existing carry-bit differences in stack RAM; no full native-oracle pass is claimed. See `measurements/2026-11-11-external-storage.json`.

### Interrupt-boundary correctness follow-up

The memory figures and four oracle failures in the preceding section describe the earlier memory-only checkpoint. The subsequent translator fix preserves all status flags at each block entry, where a cycle-budget escape can service an interrupt. All 6,000 native checkpoints now match the host exactly, with unchanged PCM. Independent boundary tests fail before the fix and pass afterward. Current external-storage Fast reservation is 1,807,840 bytes, an increase of 23,696 bytes over that memory-only checkpoint; the CPU-only test uses about 1.64% more cycles. A separate 2 MiB Fast PAL coldboot still reaches gameplay. Neither full-speed nor zero-Fast acceptance is established. See `measurements/2026-11-11-interrupt-flags.json` for exact tests and the fixed-endpoint target comparison.

### Corrected compact rendering and measured speed

The existing `--compact-rowkey` option has now been requalified on the corrected native baseline. It retains exact native state/PCM and passes the guarded host and native sprite-fixture comparisons; defaults remain unchanged. See `measurements/2026-11-11-corrected-rowkey.json`.

A separate no-input PAL 68020/2 MiB Chip + 2 MiB Fast interval, inferred from independent coldboots at fields 9,000 and 15,000, averages 25.79 source frames/second for compact versus 25.57 for corrected legacy. Compact reaches about 42.9% of the original 60.10 Hz game rate, not 100%. This is expanded-memory emulator evidence, not zero-Fast stock or physical-hardware acceptance. See `measurements/2026-11-11-postboot-speed.json` for exact settings, endpoints and limitations.
