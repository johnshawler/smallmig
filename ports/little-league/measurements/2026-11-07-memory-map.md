# Linked memory map

Linked layout checked against ELF; runtime addresses require a separately observed relocated base

| Resource | Linked address | Bytes | Type |
| --- | ---: | ---: | --- |
| .text | $00200000 | 354,392 | Fast |
| .data | $00256858 | 32 | Fast |
| .rom | $00256878 | 262,144 | Fast |
| .bss | $00296880 | 2,186,404 | Fast |
| .stack | $004AC524 | 16,384 | Fast |
| .chipbuf | $00001000 | 1,109,384 | Chip |

## Placement checks

- CPU code, ROM, stack, dispatch tables, renderer metadata and interrupt handlers are in Fast RAM
- Displayed bitmaps, Copper lists and Paula sample buffers are in Chip RAM
- The bootloader requests MEMF_FAST dynamically; linked base is not a guaranteed load address
- The boot staging allocation occurs before takeover; it is not added to steady-state buffers as if live simultaneously
- OS/loader coexistence and physical expansion bus width are not measured by this static audit
- Redundant fallback hw_static reserves 1036312 Fast bytes although the player supplies Chip output buffers; candidate removal needs a separate check

## Large allocations and interrupt code

| Symbol | Linked address | Bytes | Type |
| --- | ---: | ---: | --- |
| hwmem | $00006484 | 1,036,316 | Chip |
| hw_static | $002F1F58 | 1,036,312 | Fast |
| nes | $002A436C | 71,934 | Fast |
| lfsr_seq | $0040ACA2 | 65,536 | Fast |
| lfsr_pos | $0041ACA2 | 65,536 | Fast |
| tab_fix | $0042C524 | 65,536 | Fast |
| tab_win6 | $0043C524 | 65,536 | Fast |
| tab_win5 | $0044C524 | 65,536 | Fast |
| tab_win4 | $0045C524 | 65,536 | Fast |
| tab_win3 | $0046C524 | 65,536 | Fast |
| tab_win2 | $0047C524 | 65,536 | Fast |
| tab_win1 | $0048C524 | 65,536 | Fast |
| tab_win0 | $0049C524 | 65,536 | Fast |
| bgrow | $002B8EA4 | 65,280 | Fast |
| spr_sh | $002E2F50 | 61,440 | Fast |
| cfgs | $003EEF70 | 57,920 | Fast |
| rt_apu | $00297148 | 53,480 | Fast |
| ar_planes | $003FD1B0 | 38,400 | Fast |
| cop | $001034A0 | 32,768 | Chip |
| spr_sg | $002DD550 | 23,040 | Fast |
| cue_noil | $000013A4 | 20,480 | Chip |
| ar_scene | $002CFAD4 | 17,304 | Fast |
| ar_out | $002CB91C | 16,824 | Fast |
| edge_cache | $00406C80 | 16,416 | Fast |
| c2p2 | $002D3EC0 | 16,384 | Fast |
| c2p1 | $002D7EC0 | 16,384 | Fast |
| plat_buf | $0010C100 | 15,360 | Chip |
| rsw | $002B6EC2 | 7,680 | Fast |
| ppu_fp_run | $002439AC | 6,786 | Fast |
| bgkey | $002C8E94 | 6,720 | Fast |
| fp_piece | $0024116C | 6,452 | Fast |
| cpu_step | $00245D6C | 5,248 | Fast |
| fp_line | $0023FFC6 | 4,518 | Fast |
| bgtab | $002CA8D8 | 4,096 | Fast |
| pcm8_value | $0042ACA3 | 4,096 | Fast |
| plat_isr_vbl_c | $0024ED78 | 274 | Fast |
| plat_isr_audio_c | $0024E628 | 228 | Fast |
| plat_isr_ports_c | $0024EC5E | 178 | Fast |
| plat_isr_ciab_c | $0024ED10 | 102 | Fast |
