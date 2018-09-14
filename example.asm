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


; Start of PRG
	.org $C000

RESET:
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

vblankwait1:
	BIT $2002
	BPL vblankwait1

clrmem:
	LDA #$00
	STA $0000, x
	STA $0100, x
	STA $0300, x
	STA $0400, x
	STA $0500, x
	STA $0600, x
	STA $0700, x
	LDA #$FE
	STA $0200, x
	INX
	BNE clrmem

vblankwait2:
	BIT $2002
	BPL vblankwait2

LoadPalettes:
	LDA $2002
	LDA #$3F
	STA $2006
	LDA #$00
	STA $2006
	LDX #$00
LoadPalettesLoop:
	LDA palettes, x
	STA $2007
	INX
	CPX #$20
	BNE LoadPalettesLoop

	LDA #$00
	STA frameCounter

	LDA #%10010000
	STA $2000
	LDA #%00011110
	STA $2001


EndlessLoop:
	JMP EndlessLoop


; Fires on vblank
NMI:
	PHA
	TXA
	PHA
	TYA
	PHA

	LDA $2002
	LDA #$00
	STA $2003
	LDA #$02
	STA $4014

	LDA #%10010000
	STA $2000
	LDA #%00011110
	STA $2001

	LDA #$00
	STA $2005
	STA $2005

	LDX frameCounter
	LDA sinTable, x
	STA $0200
	LDA cosTable, x
	STA $0203
	INX
	STX frameCounter

	LDA #$00
	STA $0201
	STA $0202

	PLA
	TAY
	PLA
	TAX
	PLA
	RTI


sinTable:
.db $80, $82, $83, $85, $86, $88, $89, $8B, $8C, $8E, $90, $91, $93, $94, $96, $97
.db $98, $9A, $9B, $9D, $9E, $A0, $A1, $A2, $A4, $A5, $A6, $A7, $A9, $AA, $AB, $AC
.db $AD, $AE, $AF, $B0, $B1, $B2, $B3, $B4, $B5, $B6, $B7, $B8, $B8, $B9, $BA, $BB
.db $BB, $BC, $BC, $BD, $BD, $BE, $BE, $BE, $BF, $BF, $BF, $C0, $C0, $C0, $C0, $C0
.db $C0, $C0, $C0, $C0, $C0, $C0, $BF, $BF, $BF, $BE, $BE, $BE, $BD, $BD, $BC, $BC
.db $BB, $BB, $BA, $B9, $B8, $B8, $B7, $B6, $B5, $B4, $B3, $B2, $B1, $B0, $AF, $AE
.db $AD, $AC, $AB, $AA, $A9, $A7, $A6, $A5, $A4, $A2, $A1, $A0, $9E, $9D, $9B, $9A
.db $98, $97, $96, $94, $93, $91, $90, $8E, $8C, $8B, $89, $88, $86, $85, $83, $82
.db $80, $7E, $7D, $7B, $7A, $78, $77, $75, $74, $72, $70, $6F, $6D, $6C, $6A, $69
.db $68, $66, $65, $63, $62, $60, $5F, $5E, $5C, $5B, $5A, $59, $57, $56, $55, $54
.db $53, $52, $51, $50, $4F, $4E, $4D, $4C, $4B, $4A, $49, $48, $48, $47, $46, $45
.db $45, $44, $44, $43, $43, $42, $42, $42, $41, $41, $41, $40, $40, $40, $40, $40
.db $40, $40, $40, $40, $40, $40, $41, $41, $41, $42, $42, $42, $43, $43, $44, $44
.db $45, $45, $46, $47, $48, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52
.db $53, $54, $55, $56, $57, $59, $5A, $5B, $5C, $5E, $5F, $60, $62, $63, $65, $66
.db $68, $69, $6A, $6C, $6D, $6F, $70, $72, $74, $75, $77, $78, $7A, $7B, $7D, $7E

cosTable:
.db $C0, $C0, $C0, $C0, $C0, $C0, $BF, $BF, $BF, $BE, $BE, $BE, $BD, $BD, $BC, $BC
.db $BB, $BB, $BA, $B9, $B8, $B8, $B7, $B6, $B5, $B4, $B3, $B2, $B1, $B0, $AF, $AE
.db $AD, $AC, $AB, $AA, $A9, $A7, $A6, $A5, $A4, $A2, $A1, $A0, $9E, $9D, $9B, $9A
.db $98, $97, $96, $94, $93, $91, $90, $8E, $8C, $8B, $89, $88, $86, $85, $83, $82
.db $80, $7E, $7D, $7B, $7A, $78, $77, $75, $74, $72, $70, $6F, $6D, $6C, $6A, $69
.db $68, $66, $65, $63, $62, $60, $5F, $5E, $5C, $5B, $5A, $59, $57, $56, $55, $54
.db $53, $52, $51, $50, $4F, $4E, $4D, $4C, $4B, $4A, $49, $48, $48, $47, $46, $45
.db $45, $44, $44, $43, $43, $42, $42, $42, $41, $41, $41, $40, $40, $40, $40, $40
.db $40, $40, $40, $40, $40, $40, $41, $41, $41, $42, $42, $42, $43, $43, $44, $44
.db $45, $45, $46, $47, $48, $48, $49, $4A, $4B, $4C, $4D, $4E, $4F, $50, $51, $52
.db $53, $54, $55, $56, $57, $59, $5A, $5B, $5C, $5E, $5F, $60, $62, $63, $65, $66
.db $68, $69, $6A, $6C, $6D, $6F, $70, $72, $74, $75, $77, $78, $7A, $7B, $7D, $7E
.db $80, $82, $83, $85, $86, $88, $89, $8B, $8C, $8E, $90, $91, $93, $94, $96, $97
.db $98, $9A, $9B, $9D, $9E, $A0, $A1, $A2, $A4, $A5, $A6, $A7, $A9, $AA, $AB, $AC
.db $AD, $AE, $AF, $B0, $B1, $B2, $B3, $B4, $B5, $B6, $B7, $B8, $B8, $B9, $BA, $BB
.db $BB, $BC, $BC, $BD, $BD, $BE, $BE, $BE, $BF, $BF, $BF, $C0, $C0, $C0, $C0, $C0


palettes:
	.db $0F, $0F, $0F, $0F
	.db $0F, $0F, $0F, $0F
	.db $0F, $0F, $0F, $0F
	.db $0F, $0F, $0F, $0F

	.db $0F, $2A, $0F, $0F
	.db $0F, $0F, $0F, $0F
	.db $0F, $0F, $0F, $0F
	.db $0F, $0F, $0F, $0F


; Interrupt vectors
	.pad $FFFA
	.dw NMI
	.dw RESET
	.dw 0


; Start of CHR
	.org $0000
	.incbin "example.chr"
