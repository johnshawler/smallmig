# Source speed and Amiga optimization priorities

Measured 7 November 2026, using the verified USA cartridge and the existing
Watch Game controller script. Counts and reproduction tools are public; cartridge
bytes, firmware, screenshots and game disks stay private.

## Real NES speed

A fresh 6,000-frame Mesen headless run reported NTSC and a CPU clock of
1,789,773 Hz. Between completed frames 1,600 and 2,200, the CPU advanced
17,868,301 cycles: 29,780.5017 cycles per frame, **60.0988 Hz**, or
**16.6393 ms per frame**. The clock value is Mesen's rounded integer frequency.
PPU master-clock deltas were 357,364 or 357,368 ticks, consistent with the
alternating rendered NTSC frame lengths and CPU/PPU boundary sampling.

This is emulated hardware time. The headless test runner is unthrottled; its
host wall-clock throughput is not the original game's speed.

Comparing every pixel of consecutive Mesen output frames gave:

| Frame interval | Changed pictures | Repeated pictures |
| --- | ---: | ---: |
| 1,600–1,800 | 13 | 187 |
| 1,800–2,000 | 110 | 90 |
| 2,000–2,200, active field sequence | 200 | 0 |

The mixed interval has 277 repeated pictures, but the active field sequence
changes every frame. The current contract is **60.0988 Hz source updates** with **PAL presentation
near 50 Hz**. Source updates have a 16.6393 ms budget; 50 pictures/s corresponds
to 20 ms per completed picture, not a slower game loop.
Unchanged-picture reuse helps static scenes; it is not a solution for all gameplay.

Mesen's ROM instruction histogram concentrates 44.79% of observed instructions
in the RAM-flag wait at CC09/CC0C and PPU-status wait at CDFE/CE01/CE03. The static
translator already recognizes both forms and skips whole wait iterations up to
the next event deadline. Their native entry blocks plus the adjacent clear-wait
block accounted for only about 0.071% of the mixed native profile. Faster polling
is not the next major gain. This small figure excludes their runtime helpers:
`rt_skip`, `xrt_skip_c` and `ppu_predict_hit` together account for another 0.696%
in this sample. Event-state processing reached through those helpers is counted
in the PPU/time-model categories, so the entry-block figure is not the complete
cost of advancing through waits.

## Where native work goes

Fresh execution of the actual wide-renderer 68020 payload in Musashi passed all
four reference checkpoints through 2,201 frames. Profiling attributes each
instruction's core cycles to its address, including variable instruction costs.
It does not model Amiga Chip RAM arbitration, DMA playback, display pacing or
cache/memory timing, and must not be converted into a hardware speed claim.

| Native category | Mixed frames 1,600–2,200 | Active frames 2,000–2,200 |
| --- | ---: | ---: |
| Planar renderer | 37.61% | 41.80% |
| PPU processing | 25.57% | 15.94% |
| Translated game code | 7.63% | 13.54% |
| Dispatch and I/O helpers | 5.01% | 7.09% |
| Time model | 5.64% | 6.22% |
| Exact APU | 9.99% | 5.94% |
| Other runtime work | 4.05% | 4.53% |
| Test-hook work, including PCM hashing | 4.49% | 4.94% |

Percentages include the test harness in the denominator. The player does not
compute its PCM hash. The harness also omits Amiga display-list construction,
audio DMA waits, interrupts and actual bus contention. Native function categories
are attribution for choosing work, not complete player frame-time percentages.

In active play, `hw_line` sprite composition accounts for 22.46% of all measured
core cycles, `ensure_trow` background tile updates for 8.04%, and `hw_region`
for 4.45%. These are the first functions to improve. In the mixed interval,
`fetch_tile` alone costs 7.50%, falling to 2.79% in the active field interval.
Scene-dependent PPU work needs both types of coverage.

The 16-bit and 32-bit payloads were also profiled over the same mixed window.
Their modeled CPU work differed by only 0.034%; the wider fetch path's intended
gain is bus availability. In stock-timed cloud FS-UAE, the separate active-display
Chip-write fixture dropped from 5,712 to 2,979 E-clock ticks, about 48% less time,
with every output pixel still matching. This is not a 48% whole-game speedup.

The earlier complete stock PAL A1200 exact-audio profile took 1,778 game-clock
ticks for 600 source frames, about 33.75% speed, approximately 20.3 source frames
per second. That build needs nearly a threefold total speedup to reach the
original NES clock. Reaching 50 source updates/s would still be below the
required original timeline; it is not the acceptance target. The latest wider renderer has no fresh complete stock-speed
measurement yet. Existing public cloud jobs use original fixtures; a full-game
cloud profile requires the cartridge and firmware in a private runner.

## Ordered solutions

1. **Reduce native sprite composition and background work.** Track changed
   sprites and their old/new screen extents, retain unaffected planar rows, and
   avoid constructing and comparing a twelve-word sprite key for every scanline
   when its inputs are already known unchanged. Use predecoded shifted/flipped
   tile rows for changed sprites. Keep priority-behind-background, clipping,
   overlap order and mid-frame OAM changes in the validity rules. This addresses
   the largest measured active-play cost without discarding animation frames.
   A hardware-sprite fast path for suitable ball/player objects is a further
   candidate, with bitmap fallback for palette, priority or channel conflicts;
   it has not been implemented or proven 1:1.
2. **Reduce PPU work duplicated by native rendering.** Broaden the existing
   state-only and whole-line batching paths on lines represented by native
   bitmaps. Compute sprite-zero hit/overflow and register timing without fetching
   full output tiles unnecessarily. Retain exact rendering for affected lines
   and invalidate on CHR/mirroring/scroll/palette changes. Compare every access
   against the per-dot model, not just final RAM, before accepting this change.
3. **Use wider AGA DMA and keep program/data in Fast RAM.** The opt-in wide
   renderer has passed every synthetic pixel and native full-match state check.
   Profile the actual player under stock A1200 timing before making it default.
   Do not substitute fast-CPU emulator mode or a larger accelerator for this
   measurement.
4. **Optimize exact sound in the remaining budget.** Replace hot queue-merging
   and integer integration loops with measured 68020 fast paths, using bounded
   relative timestamps where proven safe. Preserve non-linear mixing and sample
   boundaries; require existing APU checks and complete PCM identity. The older
   approximate Paula cue mode is not 1:1 sound acceptance.
5. **Translate selected game routines only after graphics costs fall.** The
   game already runs through native translation. In the active CPU-only sample,
   even eliminating the translated/dispatch/helper buckets entirely would offer
   only about a 26% upper-bound speedup in that model; optimizing a subset offers
   less. This alone cannot supply the nearly threefold improvement suggested by
   the older whole-system measurement.

The supplied optimization brief supersedes the intermediate proposal to convert
logic to 50 Hz. Retain the original **60.0988 Hz source-clock accumulator** and
sample input and synthesize sound for every source update. PAL presentation runs
separately near 50 Hz. A 20 ms picture budget is not a 20 ms source-update budget.
The existing CIA source clock already has the correct rate.

The player previously advanced its clock origin when more than eight updates
late. That hides accumulated debt. The continuation removes that adjustment and
records current/full high-water logic debt. This reports a missed deadline
honestly; it does not make an overloaded engine catch up or provide a fully
incremental renderer. Picture age, frozen event-segment snapshots and bounded
render jobs remain further work.

## Reproduction

From the Small Mig root, with private inputs available:

```sh
python3 ports/little-league/mesen_speed.py --rom /private/little-league.nes --mesen /path/to/Mesen
python3 ports/little-league/native_check.py --payload ports/little-league/vendor/build/native-wide/llb.elf --states /private/game-states.bin --musashi /path/to/musashi --frames 2201 --profile --first 2000 --last 2200
```

The native checker requires an already built private payload and matching host
STATEOUT checkpoints. Its optional profile does not modify emulated memory or
instructions. Structured results are in `measurements/2026-11-07-speed.json`.
The latest player ADF is unchanged by this measurement work.
