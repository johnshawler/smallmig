# RAM and renderer continuation

The supplied optimization brief is the current contract. Its Punch-Out results
and reported Baseball/Excitebike experiments are leads, not measurements of this
port. Preserve original rules, object counts, first-eight sprite selection,
priority, input sampling and exact PCM. The USA source clock remains 60.0988 Hz;
PAL presentation is a separate quantity. Do not convert logic to 50 Hz.

## Compact exact sprite-row identity

| Field | Record |
| --- | --- |
| Hypothesis | A sprite-row cache hit should not require clearing a twelve-word temporary key, overwriting active slots and comparing unused slots. The active-field profile attributes 22.46% of modeled native cycles to `hw_line`. |
| Baseline | Stock 020 target, PAL AGA, 2 MiB Chip + 8 MiB Fast; 32-bit fetch path, exact PCM, legacy key. Paired native builds use the same compiler/flags plus `AR_CACHE_STATS`. Source window 2,000–2,200; Watch Game input SHA-256 `d56dbffdf0a213720e5ef237bc5faf2762fd97bf57163f44f59eda4d32b4597b`. |
| Change | Opt-in `AR_COMPACT_ROWKEY` / wrapper `--compact-rowkey`: compare count/control/banks/clip, the selected sprite words, and conditional background dependencies. Compare/copy only meaningful slots. No hash and no new allocation. |
| Memory | Existing Fast key storage remains 2 buffers × 240 rows × 48 bytes = 23,040 bytes, plus 48-byte shared scratch. At most eight selected OAM words are inspected per row; unused slots need no clearing. Four 32-bit counters are test instrumentation. |
| Validity | Selected raw OAM words include Y, X, pattern, palette, flips and background priority. Header includes count, sprite size, pattern table and clipping; bank identity is explicit. Behind-background sprites also depend on background row/window/config generation. Palette-only changes do not invalidate indexed pixels. The accepted cartridge has immutable CHR ROM; this does not prove a general CHR-RAM cache. |
| Preparation | Reuses existing static arenas and the existing first-eight lists. Their membership guards and mid-frame OAM resnapshot behavior are unchanged. |
| Miss path | Same composition/priority/dirty-longword path as baseline. `AR_NOROWCACHE` forces rebuilds. The legacy key remains available without `AR_COMPACT_ROWKEY`. A row can write at most 4 × 32 output bytes, with unchanged longwords suppressed. |
| Correctness | Cached and forced-rebuild modes each passed nine 6,000-frame per-dot/planar scripts, 5,999 picture comparisons per script, and 588 APU checks. Native candidate completed 100,001 frames and all 11 RAM/OAM/palette/nametable checkpoints. Separate 6,000-frame native PCM matched the independent host stream hash 1246956292. |
| CPU-only performance | Paired active-field profiles: 176,760,193 → 170,818,314 core cycles (3.36% less total modeled work). Renderer category: 73,996,940 → 68,055,061 (8.03% less). Both had 172,666 calls, 132,243 hits, 40,423 misses and 584,383 OAM words inspected through frame 2,201. Lookup, validation and copying are included. |
| Cache coverage | Candidate full match: 8,071,322 calls, 6,546,145 hits, 1,525,177 misses. This coverage alone is not a speed claim. Worst isolated cache-miss elapsed cost is not yet measured. |
| Target check | New original-data fixture executes the actual renderer and Copper builder from Fast RAM with stock PAL 020 timing, JIT disabled, active display and Paula DMA. It compares legacy, compact and forced rebuilds against an independent first-eight/pixel oracle. It records aggregate, median, 95th percentile and maximum renderer elapsed time; diagnostic hashing is excluded. Full-game APU CPU synthesis is not included in this fixture. |
| Decision | Target renderer timing and pixel checks passed in cloud run 42409042176: mean renderer elapsed fell 85.26 → 78.82 ms (7.55% less); worst call fell 113.76 → 107.32 ms. Retained opt-in while full-player timing remains open. A renderer microbenchmark does not certify the full player's update rate, picture age, input latency, uninterrupted audio or physical hardware. |

The target fixture includes transparent sprites occupying selection slots,
oversubscribed lines, overlap and behind-background priority, clipping, both
flips, 8×8/8×16 changes, fine scrolling and CHR bank changes. Across all 64
states it checks the actual native sprite-plane stream against the independent
oracle; its final screenshot checks every displayed pixel through the Copper.
The game coverage scripts supply additional mid-frame event cases.

The first target run rejected a call longer than the 16-bit E-clock range.
The timer now resolves counter wraps using the independent source-clock count,
instead of reporting a truncated stall. Its wrap reconstruction passed 100,000
deterministic counter-phase/duration cases. Target measurements are inclusive
elapsed renderer time under interrupts/DMA; do not add those interrupt costs a
second time to a CPU budget.

The target comparison used 64 states per mode. Legacy and compact each had
15,360 cache calls, 6,928 hits and 8,432 misses. Forced rebuild had no hits and
identical visible output. Its aggregate mean was 83.69 ms, but its median and
upper-tail times were lower than compact caching. Thus the cache is not a
universal per-call win; retain the forced-rebuild path for further profiling.

Exact build hashes, profiles and correctness counts are in
`measurements/2026-11-07-rowkey.json`. The last delivered ADF remains unchanged.

## Memory audit

The build now exports a checked `memory-map.json` and human-readable
`memory-map.md`. Linked addresses are explicitly distinguished from an observed
relocated runtime base. Code, cartridge data, the stack, dispatch tables, renderer
keys and interrupt handlers are Fast; live bitmaps, Copper and Paula buffers
are Chip. A representative map is in `measurements/2026-11-07-memory-map.md`.

Baseline allocation is 2,819,204 Fast bytes, 1,109,384 Chip output bytes and
654,848 bytes of Chip boot staging. Staging happens before takeover and is not
silently summed into steady-state output buffers as if all remain live. OS/loader
peak coexistence and physical expansion bus width remain unmeasured.

The audit found an unused `hw_static` fallback occupying 1,036,312 Fast bytes.
The player supplies separate Chip output storage. Removing that fallback is a
separate candidate for lower RAM demand and cold-start clearing cost, not a
claimed gameplay frame-rate improvement. It is unchanged in the paired row-key
experiment. Predecoded shifted/flipped sprite rows can later use bounded reclaimed
Fast storage, subject to a measured lookup/miss path.

## Clock/debt correction and remaining scheduler work

The source-rate CIA timer is retained. The player previously shifted `game_base`
when more than eight updates late, losing the original source deadlines.
That adjustment is removed; current and high-water debt are retained in telemetry.
The player elapsed-work counters now also recover fine-counter wraps instead
of truncating long calls at roughly 92 ms. This exposes overload rather than
resolving it. Native state/PCM tests bypass
player hardware pacing, so they are not timing proof for this correction.

The default generated profile is now stock PAL 68EC020, 2 MiB Chip and 8 MiB Fast,
with cycle timing enabled and JIT disabled. `--fast-cpu` is an explicit accelerated
playtest mode. Source clock and presentation mode remain independent.

Still required: full-player deadline/latency and picture-age measurements, frozen
event-segment snapshots, bounded render jobs, publication ownership for all shared
persistent backgrounds, startup/transition audio playback and physical testing.
The existing sprite/exact layers have per-buffer cache records; that is not a
proof that every shared background write is safe against live display DMA.
No WHDLoad slave is supplied by this continuation; its allocation/cache contract
would need its own implementation and tests.
