; SPDX-License-Identifier: 0BSD
; Original test written for this harness, not copied from a game.
; NES-style binary ADC. Zero page: x, delta, wall, score, hit.
; delta is an 8-bit displacement, usually 0, 1, or $ff (-1).
; Every call moves x modulo 256; exact contact scores once per call.
.org $8000
step:
    LDA $00
    CLC
    ADC $01
    STA $00
    CMP $02
    BNE no_hit
    LDA #$01
    STA $04
    INC $03
    RTS
no_hit:
    LDA #$00
    STA $04
    RTS
