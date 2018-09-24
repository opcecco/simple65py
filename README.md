# simple65py

_simple65py_ is a simple assembler for the MOS 6502 CPU.
It was created to assemble games for the Nintendo Entertainment System (NES), but should work for any system that uses the 6502 as it's main processor.

# Usage

```
python3 simple65.py INPUTFILE OUTPUTFILE
```
Where INPUTFILE is a 6502 assembly code file, and OUTPUTFILE is the resulting binary file.

Included is some example code that assembles into an NES binary. To assemble the example code:
```
python3 simple65.py example.asm example.nes
```
The resulting NES ROM binary can be run in an NES emulator.

# 6502 Assembly

## Opcodes

A full list of 6502 opcodes can be found [here](http://www.6502.org/tutorials/6502opcodes.html).

## Directives

### .ORG (Origin PC)

```
.ORG value
```

Sets the internal program counter to the specified value.

### .PAD (Pad PC)

```
.PAD value
```

Pads the binary with zeros until the program counter reaches the specified value.

### .DB (Data byte)

```
.DB byte1, byte2, ..., byteN
```

Inserts the specified value or list of values into the binary as individual bytes.

### .DW (Data word)

```
.DW word1, word2, ..., wordN
```

Inserts the specified value or list of values into the binary as individual words (2-byte values).
Words are inserted little-endian style (least significant byte first).

### .RS (Reserve byte)

```
.RS count
```

Reserves a series of bytes according to the count.
This modifies the internal program counter, but does not insert any bytes into the binary.

### .DEF (Define)

```
.DEF label value
```

Defines a label as the specified value.

### .INCLUDE (Include code)

```
.INCLUDE "filename"
```

Includes the specified file and parse it as assembly code.

### .INCBIN (Include binary)

```
.INCBIN "filename"
```

Includes the specified file as raw binary.
