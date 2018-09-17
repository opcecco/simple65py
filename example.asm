; Example 6502 ASM file for simple65py by Oliver Ceccopieri
; Circular movement demo for Nintendo Entertainment System

; iNES header
	.db 'N', 'E', 'S', $1A

	.db $01, $01 ; PRG and CHR bank count
	.db $00      ; Mapper 0 and mirroring 0

; clear remaining bytes of header
	.db $00, $00, $00, $00, $00, $00, $00, $00, $00


; RAM address labels (variables)
	.org $0000

frameCounter: .rs 1


; Start of PRG (code/data)
	.org $C000

; This routine runs when the NES is powered on or reset
RESET:

; Set up the stack and PPU ports
	SEI
	CLD
	LDX #$40
	STX $4017
	LDX #$FF
	TXS
	INX
	STX $2000
	STX $2001
	STX $4010

; Wait for the first vblank
vblankwait1:
	BIT $2002
	BPL vblankwait1

; Clear all RAM
clrmem:
	LDA #$00
	STA $0000, X
	STA $0100, X
	STA $0300, X
	STA $0400, X
	STA $0500, X
	STA $0600, X
	STA $0700, X
	LDA #$FE
	STA $0200, X
	INX
	BNE clrmem

; Wait for second vblank
vblankwait2:
	BIT $2002
	BPL vblankwait2

; Load color palettes for our sprite
LoadPalettes:
	LDA $2002
	LDA #$3F
	STA $2006
	LDA #$00
	STA $2006
	LDX #$00
LoadPalettesLoop:
	LDA palettes, X
	STA $2007
	INX
	CPX #$20
	BNE LoadPalettesLoop

; Initialize the frame counter
	LDA #$00
	STA <frameCounter

; Enable sprites and NMI
	LDA #%10010000
	STA $2000
	LDA #%00011110
	STA $2001


; Endless loop, the Non-Maskable Interrupt does most of the work
EndlessLoop:
	JMP EndlessLoop


; Non-Maskable Interrupt, fires on vblank
NMI:

; Push registers and flags onto the stack
	PHA
	TXA
	PHA
	TYA
	PHA


; Begin drawing our sprites in a loop
	LDX #$00
SpriteLoop:

; Offset the frame counter per sprite
	LDA <frameCounter
	SEC
	SBC sprites, X
	TAY

; Set the sprite Y position according to the sine table
	LDA sinTable, Y
	STA $0200, X
	INX

; Set the sprite tile
	LDA sprites, X
	STA $0200, X
	INX

; Set the sprite palette
	LDA sprites, X
	STA $0200, X
	INX

; Set the sprite X position according to the cosine table
	LDA cosTable, Y
	STA $0200, X
	INX

; If X < 32, keep drawing, else increment the frame counter and continue
	CPX #$20
	BNE SpriteLoop
	INC <frameCounter

; Copy sprite data to the PPU
	LDA $2002
	LDA #$00
	STA $2003
	LDA #$02
	STA $4014

; Update the PPUCTRL and PPUMASK ports
	LDA #%10010000
	STA $2000
	LDA #%00011110
	STA $2001

; Update scroll
	LDA #$00
	STA $2005
	STA $2005

; Pull registers and flags back off the stack
	PLA
	TAY
	PLA
	TAX
	PLA
	RTI


; Table of Y-positions (sine)
sinTable:
	.db $6E, $6C, $6A, $68, $66, $64, $62, $60, $5E, $5D, $5B, $59, $57, $55, $53, $51
	.db $50, $4E, $4C, $4A, $49, $47, $45, $44, $42, $40, $3F, $3D, $3C, $3A, $39, $37
	.db $36, $35, $33, $32, $31, $30, $2F, $2D, $2C, $2B, $2A, $29, $29, $28, $27, $26
	.db $25, $25, $24, $23, $23, $22, $22, $22, $21, $21, $21, $20, $20, $20, $20, $20
	.db $20, $20, $20, $20, $21, $21, $21, $22, $22, $22, $23, $23, $24, $25, $25, $26
	.db $27, $28, $29, $29, $2A, $2B, $2C, $2D, $2F, $30, $31, $32, $33, $35, $36, $37
	.db $39, $3A, $3C, $3D, $3F, $40, $42, $44, $45, $47, $49, $4A, $4C, $4E, $50, $51
	.db $53, $55, $57, $59, $5B, $5D, $5E, $60, $62, $64, $66, $68, $6A, $6C, $6E, $70
	.db $72, $74, $76, $78, $7A, $7C, $7E, $80, $82, $83, $85, $87, $89, $8B, $8D, $8F
	.db $90, $92, $94, $96, $97, $99, $9B, $9C, $9E, $A0, $A1, $A3, $A4, $A6, $A7, $A9
	.db $AA, $AB, $AD, $AE, $AF, $B0, $B1, $B3, $B4, $B5, $B6, $B7, $B7, $B8, $B9, $BA
	.db $BB, $BB, $BC, $BD, $BD, $BE, $BE, $BE, $BF, $BF, $BF, $C0, $C0, $C0, $C0, $C0
	.db $C0, $C0, $C0, $C0, $BF, $BF, $BF, $BE, $BE, $BE, $BD, $BD, $BC, $BB, $BB, $BA
	.db $B9, $B8, $B7, $B7, $B6, $B5, $B4, $B3, $B1, $B0, $AF, $AE, $AD, $AB, $AA, $A9
	.db $A7, $A6, $A4, $A3, $A1, $A0, $9E, $9C, $9B, $99, $97, $96, $94, $92, $90, $8F
	.db $8D, $8B, $89, $87, $85, $83, $82, $80, $7E, $7C, $7A, $78, $76, $74, $72, $70

; Table of X-positions (cosine)
cosTable:
	.db $D0, $D0, $D0, $D0, $CF, $CF, $CF, $CE, $CE, $CE, $CD, $CD, $CC, $CB, $CB, $CA
	.db $C9, $C8, $C7, $C7, $C6, $C5, $C4, $C3, $C1, $C0, $BF, $BE, $BD, $BB, $BA, $B9
	.db $B7, $B6, $B4, $B3, $B1, $B0, $AE, $AC, $AB, $A9, $A7, $A6, $A4, $A2, $A0, $9F
	.db $9D, $9B, $99, $97, $95, $93, $92, $90, $8E, $8C, $8A, $88, $86, $84, $82, $80
	.db $7E, $7C, $7A, $78, $76, $74, $72, $70, $6E, $6D, $6B, $69, $67, $65, $63, $61
	.db $60, $5E, $5C, $5A, $59, $57, $55, $54, $52, $50, $4F, $4D, $4C, $4A, $49, $47
	.db $46, $45, $43, $42, $41, $40, $3F, $3D, $3C, $3B, $3A, $39, $39, $38, $37, $36
	.db $35, $35, $34, $33, $33, $32, $32, $32, $31, $31, $31, $30, $30, $30, $30, $30
	.db $30, $30, $30, $30, $31, $31, $31, $32, $32, $32, $33, $33, $34, $35, $35, $36
	.db $37, $38, $39, $39, $3A, $3B, $3C, $3D, $3F, $40, $41, $42, $43, $45, $46, $47
	.db $49, $4A, $4C, $4D, $4F, $50, $52, $54, $55, $57, $59, $5A, $5C, $5E, $60, $61
	.db $63, $65, $67, $69, $6B, $6D, $6E, $70, $72, $74, $76, $78, $7A, $7C, $7E, $80
	.db $82, $84, $86, $88, $8A, $8C, $8E, $90, $92, $93, $95, $97, $99, $9B, $9D, $9F
	.db $A0, $A2, $A4, $A6, $A7, $A9, $AB, $AC, $AE, $B0, $B1, $B3, $B4, $B6, $B7, $B9
	.db $BA, $BB, $BD, $BE, $BF, $C0, $C1, $C3, $C4, $C5, $C6, $C7, $C7, $C8, $C9, $CA
	.db $CB, $CB, $CC, $CD, $CD, $CE, $CE, $CE, $CF, $CF, $CF, $D0, $D0, $D0, $D0, $D0


; Color palette values
palettes:
	.db $0F, $0F, $0F, $0F
	.db $0F, $0F, $0F, $0F
	.db $0F, $0F, $0F, $0F
	.db $0F, $0F, $0F, $0F

	.db $02, $2A, $0F, $0F
	.db $0F, $28, $0F, $0F
	.db $0F, $2C, $0F, $0F
	.db $0F, $24, $0F, $0F

; Sprite values
sprites:
	.db $00, 'C', $00, $00
	.db $08, 'I', $01, $00
	.db $10, 'R', $02, $00
	.db $18, 'C', $03, $00
	.db $20, 'U', $00, $00
	.db $28, 'L', $01, $00
	.db $30, 'A', $02, $00
	.db $38, 'R', $03, $00


; Interrupt vectors
	.pad $FFFA
	.dw NMI
	.dw RESET
	.dw 0


; Start of CHR (graphics)
	.org $0000
	.incbin "example.chr"
