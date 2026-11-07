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

## Fresh native fidelity and human play

- Native translated 68020 engine completed 100,001 frames, passing all 11 RAM FNV checkpoints around source frames 1,500, 6,000 and 100,000. The final hash was `0x184e22ce`, checkpoint mask `0x7ff`. This tests the native translated program and interpreter fallback against the host state, whose 2,048 RAM bytes also matched fresh Mesen checkpoints.
- Full-match test allocated Fast RAM dynamically at `0x20dcd0`, using 2 MiB Chip + 4 MiB Fast. The final scoreboard matched all 57,344 compared pixels; the bottom 16 lines contained diagnostic telemetry and were excluded. This accelerated acceptance harness draws one in 64 frames and renders exact PCM to scratch, without Paula playback; its zero audio counters are not playback evidence.
- Separate native no-telemetry scenes compared every one of 61,440 pixels: PAL menu frame 100, batting frame 1,500 and field frame 2,000; NTSC batting frame 1,500. All four had zero differences and uniform 2x2 display scaling. These are native screenshots against host reference frames, rather than all frames of every game.
- Exact 8-bit PCM lookup conversion remained byte-identical across 6,000 frames in both standards. PAL SHA-256: `0047a26726da6f154ebe1883cb98587fb7b1f85cc38eb2159451ec409721b0fe`; NTSC: `bccdc2ae0bb1cea6becef56b81aa2c27b69c16534b1dc3de88573c6472d6ff7c`.
- Human NTSC play used 68020 fast CPU mode, no JIT, 2 MiB Chip + 4 MiB Fast. Exhibition, team selection, bat toss, lineup editing, pitching, hit-to-field transition, fielding and next batter were observed. Controller input was live, with no scripted test input. Lineup commands cycle using Left/Right; choose End to begin the inning.
- Over a continuous 3,766-frame gameplay interval, the game clock, executed source frames and played PCM chunks each increased by exactly 3,766. New audio underruns: zero; new dropped APU events: zero. Five display deadlines were skipped during that interval. There were 16 cumulative audio underruns before the interval, so this does not establish flawless startup or transition playback. Audio playback was checked through DMA counters, not a listening assessment.
- Clean player ADF two-player check: both controller ports independently confirmed their teams and lineups. WASD/F/G controlled player two while Arrows/Z/X controlled player one. Batter position movement, a human pitch, and a timed human swing resulting in a hit with the ensuing ball/runner field view were observed. This is not a full human two-player match or manual baserunning acceptance.
- A 100 MHz 68060 timing profile reached about 82.8% (725 ticks for the same 600 source frames), still below full original speed. It does not change the default requirements or establish physical accelerator performance.
- Relocation tool proof: 9,701 fixups from a high-memory test image produced a byte-identical result to an independent relink at another base, with the private ROM placeholder excluded consistently. The clean player build uses 9,595 relocations and requests 2,754,656 bytes of Fast RAM.

## Native performance

Measured in FS-UAE with JIT disabled and CPU/memory/blitter cycle timing enabled. Source-frame profiling interval `[1600,2200)`; rates are approximate because the interval endpoints are sampled by the profiler interrupt.

| Configuration | Clock ticks for 600 source frames | Original speed |
|---|---:|---:|
| Baseline PAL A1200, 68EC020, 2 MiB Chip + 8 MiB Z2 Fast, cue audio | 1,429 | about 42.0% |
| Same stock profile, original exact APU mixer | 1,835 | about 32.7% |
| Same stock profile, cached exact PCM sample boundaries | 1,778 | about 33.7% |

The exact mixer category decreased from about 11.0 to 9.2 ms per source frame. With stock timing, exact sound still underruns and display frames are skipped. This does not satisfy 1:1 acceptance. The fast CPU playtest results above are separate.

Additional timed profiles reached about 44.9% on 50 MHz 68030 with Z3 memory/cache startup, 66.3% on 25 MHz 68040 and 75.6% on 50 MHz 68060. These are FS-UAE measurements, not physical accelerator certification. The 68060 startup was booted with its PCR and caches enabled; the timing result did not improve. Optional CPU-specific startup paths remain experimental.

The default wrapper now allocates Fast RAM dynamically and writes an explicitly fast CPU FS-UAE profile with JIT disabled. `--stock-timing` is a diagnostic option. Neither the faster profile nor changing the hardware target resolves stock-speed acceptance.

## Remaining acceptance gates

1. Full original speed and uninterrupted exact audio on a clearly declared hardware profile.
2. Broader native graphics comparison across transitions and mid-frame palettes beyond the four pixel-exact scenes.
3. Human baserunning, complete two-player matches, and human full matches/restarts. CPU native full-match, live pitching/fielding, batter movement and two-player hit controls have passed the checks described above.
4. Uninterrupted startup/transition audio and every-frame display timing; physical hardware validation. The clean ADF is built reproducibly from private input with documented memory requirements, but remains a development candidate.

Historical results in `vendor/docs/` belong to the pinned upstream project. They are not substituted for fresh checks here. Cartridge, firmware, decoded graphics, generated ADFs and raw reference captures are excluded from public source.
