# Current original-engine validation

Date: 2026-11-07. This is a development checkpoint, not 1:1 release acceptance.

## Fresh results

- Original Small Mig demo built and booted before port development.
- Full original-game ADF built with macOS ARM64, m68k GCC 16.2.0 and FS-UAE 3.2.35. Original introduction, menus, Exhibition selection, team selection, lineup, batting/pitching view and field camera observed on the A1200.
- `check.py --mesen ...` passed the Watch Game script and eight coverage scripts, 6,000 frames each. Each produced 5,999 planar frames identical to the internal per-dot reference. Watch Game passed 9,836,981 PPU comparisons. Frame-skipping coverage (`--draw-every 4`) was also exercised during runtime development.
- Fresh Mesen headless Watch Game run completed 100,000 frames. All 2,048 game RAM bytes matched the host runtime at completed frames 1,500, 6,000 and 100,000 (runtime hooks 1,499, 5,999 and 99,999 respectively).
- The original game reached the final New York 2–California 1 scoreboard in both Mesen and the host runtime. A 200,000-frame host run remained at that results screen without an illegal-opcode failure. This was CPU Watch Game, not human play acceptance.
- Final static scoreboard RGB image: zero differing pixels between Mesen frame 100,000 and runtime hook 100,000. Their indexing differs by one, but the final scene is static. This is a host picture comparison, not a native Amiga screenshot comparison.
- Existing APU suite: 588 checks, zero failures, including the fast renderer against its straightforward reference. The new sample-boundary cache also passed these checks. Exact PAL PCM over all 6,000 Watch Game frames was byte-identical before/after that cache: SHA-256 `0047a26726da6f154ebe1883cb98587fb7b1f85cc38eb2159451ec409721b0fe` for both private streams.

## Native performance

Measured in FS-UAE with JIT disabled and CPU/memory/blitter cycle timing enabled. Source-frame profiling interval `[1600,2200)`; rates are approximate because the interval endpoints are sampled by the profiler interrupt.

| Configuration | Clock ticks for 600 source frames | Original speed |
|---|---:|---:|
| Baseline PAL A1200, 68EC020, 2 MiB Chip + 8 MiB Z2 Fast, cue audio | 1,429 | about 42.0% |
| Same stock profile, original exact APU mixer | 1,835 | about 32.7% |
| Same stock profile, cached exact PCM sample boundaries | 1,778 | about 33.7% |

The exact mixer category decreased from about 11.0 to 9.2 ms per source frame. Exact sound still underruns badly at the current overall speed. The display skips frames while behind. Neither satisfies 1:1 acceptance.

An explicit 50 MHz 68030 profile with the same Z2 memory reached about 43.4% with the original exact mixer. That is not a test of accelerator-local Fast RAM. A Blizzard 1230 IV profile was blocked by missing expansion boot firmware. The build now supports a selected fast-memory link address through `FAST_BASE`; higher-memory configurations remain experimental until separately booted and measured. The default wrapper retains the stock A1200 memory profile.

## Remaining acceptance gates

1. Full original speed and uninterrupted exact audio on a clearly declared hardware profile.
2. Fresh native graphics comparison across gameplay and transitions, including mid-frame palettes.
3. Human batting, pitching, fielding, baserunning and two-player controller testing; complete native matches and restarts.
4. Release ADF identity, repeatable private build and documented hardware requirements.

Historical results in `vendor/docs/` belong to the pinned upstream project. They are not substituted for fresh checks here. Cartridge, firmware, decoded graphics, generated ADFs and raw reference captures are excluded from public source.
