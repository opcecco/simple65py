#!/usr/bin/env python3


import re
import sys

# Regex for parsing ASM code
token_regex = re.compile(
    r'(?:([A-Za-z_][\w\.\-\+]*):)?(?:\s*([^;\s]+))?(?:\s+([^;]*[^;\s]))?(?:\s*(;.*))?'
)
operand_regex = re.compile(r'([#\(])?([^,\(\)]+)(\))?(?:,\s*([^\(\)]+))?(\))?')
value_regex = re.compile(r'([<>])?([%$])?([\'"])?([^\'"]+)([\'"])?')
param_split_regex = re.compile(r'[,\s]\s*')

# Global structures
file_name_stack = []
line_count_stack = []
label_table = {}
instruction_list = []
instr_strings = {}
prog_counter = 0


# Class to store information about a single opcode and its byte representations
class Opcode:

    def __init__(self,
                 implied=None, imm=None,
                 zp=None, zp_x=None, zp_y=None,
                 abs=None, abs_x=None, abs_y=None,
                 ind=None, ind_x=None, ind_y=None,
                 off=None):
        self.length = 1
        self.implied = implied
        self.imm = imm
        self.zp = zp
        self.zp_x = zp_x
        self.zp_y = zp_y
        self.abs = abs
        self.abs_x = abs_x
        self.abs_y = abs_y
        self.ind = ind
        self.ind_x = ind_x
        self.ind_y = ind_y
        self.off = off

    def __getitem__(self, name):
        return getattr(self, name)


# Class for storing a value which can be used as an operand or binary data
class Value:

    def __init__(self, val_str, length=None):
        self.file = current_file
        self.line = current_line

        try:
            if isinstance(val_str, int):
                # If we are passed an integer, just use that as a literal
                self.truncation = 0
                self.literal = val_str
                self.label = None
                self.length = length
            else:
                # If we are passed a string, parse out the literal or label
                try:
                    tokens = value_regex.match(val_str).groups()
                except AttributeError:
                    error(self.file, self.line, 'Unable to parse value')

                # Check if we want to truncate the value
                self.truncation = (
                    1 if tokens[0] == '>'
                    else -1 if tokens[0] == '<'
                    else 0
                )

                # Get the base and literal value
                base = (
                    16 if tokens[1] == '$'
                    else 2 if tokens[1] == '%'
                    else 10 if tokens[3].isdigit()
                    else None
                )
                literal_val = (
                    int(tokens[3], base) if base is not None
                    else ord(tokens[3]) if tokens[2] and tokens[4]
                    else None
                )
                self.literal = (
                    None if literal_val is None
                    else literal_val & 0xFF if self.truncation == -1
                    else literal_val >> 8 if self.truncation == 1
                    else literal_val
                )

                # Get the label this value refers to
                self.label = tokens[3] if self.literal is None else None

                # Get the value's length
                self.length = (
                    length if length is not None
                    else 1 if self.truncation != 0 or (self.literal is not None and self.literal < 256)
                    else 2
                )
        except ValueError:
            error(self.file, self.line, 'Bad value')

    # Return a list of bytes representing this value
    def get_bytes(self):
        # Use either the literal or the value of a label
        try:
            out_val = self.literal if self.literal is not None else label_table[self.label]
        except KeyError:
            error(self.file, self.line, f'Label not found "{self.label}"')

        # Truncate the value
        if self.truncation == -1:
            out_val &= 0xFF
        elif self.truncation == 1:
            out_val >>= 8

        # Return the proper length value
        if self.length == 1:
            return [out_val]
        else:
            return [out_val & 0xFF, out_val >> 8]


# Class representing an operand
class Operand:

    # Table for looking up addressing mode based on the operand
    mode_dict = {
        ('#',  None, None, None, 1): 'imm',
        ('#',  None, None, None, 2): 'imm',
        (None, None, None, None, 1): 'zp',
        (None, None, 'X',  None, 1): 'zp_x',
        (None, None, 'Y',  None, 1): 'zp_y',
        (None, None, None, None, 2): 'abs',
        (None, None, 'X',  None, 2): 'abs_x',
        (None, None, 'Y',  None, 2): 'abs_y',
        ('(',  ')',  None, None, 1): 'ind',
        ('(',  ')',  None, None, 2): 'ind',
        ('(',  None, 'X',  ')',  1): 'ind_x',
        ('(',  ')',  'Y',  None, 1): 'ind_y',
    }

    def __init__(self, oper_str, offset=False):
        self.file = current_file
        self.line = current_line
        self.pc = prog_counter

        if oper_str:
            # Parse the operand and get a coresponding value
            try:
                tokens = operand_regex.match(oper_str).groups()
            except AttributeError:
                error(self.file, self.line, 'Unable to parse operand')

            self.value = Value(tokens[1])

            # Check if we should use the value as an offset (used for branch instructions)
            if offset:
                self.length = 1
                self.mode = 'off'
            else:
                # Generate a key to lookup the proper addressing mode in a table
                mode_key = (
                    tokens[0],
                    tokens[2],
                    tokens[3].upper() if tokens[3] else None,
                    tokens[4],
                    self.value.length,
                )
                try:
                    self.mode = Operand.mode_dict[mode_key]
                except KeyError:
                    error(self.file, self.line, 'Invalid addressing mode')

                # Adjust value length for immediate and indirect modes
                if self.mode == 'imm':
                    self.value.length = 1
                if self.mode == 'ind':
                    self.value.length = 2
                self.length = self.value.length
        else:
            self.value = None
            self.length = 0
            self.mode = 'implied'

    # Return a list of bytes representing this operand
    def get_bytes(self):
        if self.mode == 'implied':
            # Return no operand for implied mode
            return []
        elif self.mode == 'off':
            # Return a program counter offset for offset mode
            if self.value.length == 2:
                bytes = self.value.get_bytes()
                branch_addr = bytes[0] + (bytes[1] << 8)
                branch_jump = (branch_addr - self.pc - 2)
                if -128 <= branch_jump <= 127:
                    return [branch_jump % 256]
                else:
                    error(self.file, self.line,
                          'Branch destination out of range')
            else:
                return self.value.get_bytes()
        else:
            # Return the value's bytes for every other mode
            return self.value.get_bytes()


# Class representing an instruction (opcode + operand pair)
class Instruction:

    def __init__(self, opcode_str, operand_str):
        self.file = current_file
        self.line = current_line
        self.opcode_str = opcode_str
        self.opcode = opcode_table[self.opcode_str]
        self.operand = Operand(operand_str, offset=self.opcode['off'])
        self.length = self.opcode.length + self.operand.length

    # Return a list of bytes representing this instruction
    def get_bytes(self):
        out_bytes = [self.opcode[self.operand.mode]]
        if out_bytes[0] is None:
            error(self.file, self.line, 'Invalid addressing mode')
        out_bytes.extend(self.operand.get_bytes())
        return out_bytes

    # Return a debug description of the instruction
    def get_description(self):
        return f'{self.opcode_str} {self.operand.mode}'


# Class for storing a raw list of values (used for directives)
class ValueList:

    def __init__(self, values):
        self.file = current_file
        self.line = current_line
        self.values = values

    # Return a list of bytes representing all contained values
    def get_bytes(self):
        return [byte for val in self.values for byte in val.get_bytes()]

    # Return a debug description of the value list
    def get_description(self):
        return 'values'


# Print an error message and quit
def error(file, line, message):
    print('ERROR!')
    print(f'{file} ({line}): {message}')
    exit(-1)


# Directive to set the program counter
def org_directive(param):
    global prog_counter
    new_pc = Value(param).literal
    if new_pc is not None:
        prog_counter = new_pc
    else:
        raise TypeError()


# Directive to pad ROM with zeros
def pad_directive(param):
    global prog_counter
    new_pc = Value(param).literal
    if new_pc is not None:
        value_list = []
        while prog_counter < new_pc:
            value_list.append(Value(0, length=1))
            prog_counter += 1
        instruction_list.append(ValueList(value_list))
    else:
        raise TypeError()


# Directive to output data bytes
def db_directive(param):
    global prog_counter
    params = param_split_regex.split(param)
    prog_counter += len(params)
    instruction_list.append(ValueList([Value(p, length=1) for p in params]))


# Directive to output data words
def dw_directive(param):
    global prog_counter
    params = param_split_regex.split(param)
    prog_counter += len(params)
    instruction_list.append(ValueList([Value(p, length=2) for p in params]))


# Directive to define a constant
def def_directive(param):
    params = param_split_regex.split(param)
    name = params[0]
    if name not in label_table:
        val = Value(params[1]).literal
        if val is not None:
            label_table[name] = val
        else:
            raise TypeError()
    else:
        error(current_file, current_line, f'Label already exists "{name}"')


# Directive to reserve bytes by incrementing the program counter, but without outputting bytes to ROM
def rs_directive(param):
    global prog_counter
    new_pc = Value(param).literal
    if new_pc is not None:
        prog_counter += new_pc
    else:
        raise TypeError()


# Directive to include an ASM file
def include_directive(param):
    parse_file(param.strip('\'"'))


# Directive to include a file as binary
def incbin_directive(param):
    global prog_counter
    file_name = param.strip('\'"')
    try:
        with open(file_name, 'rb') as bin_file:
            bytes = bin_file.read()
    except FileNotFoundError:
        error(current_file, current_line,
              f'Binary file not found "{file_name}"')
    instruction_list.append(ValueList([Value(b, length=1) for b in bytes]))
    prog_counter += len(bytes)


# Table relating directive names to their functions
directive_table = {
    '.ORG': org_directive,
    '.PAD': pad_directive,
    '.DB': db_directive,
    '.DW': dw_directive,
    '.DEF': def_directive,
    '.RS': rs_directive,
    '.INCLUDE': include_directive,
    '.INCBIN': incbin_directive,
}


# Table relating opcodes to their valid modes and byte representations
opcode_table = {
    # Math instructions
    'ADC': Opcode(imm=0x69, zp=0x65, zp_x=0x75, abs=0x6D, abs_x=0x7D, abs_y=0x79, ind_x=0x61, ind_y=0x71),
    'AND': Opcode(imm=0x29, zp=0x25, zp_x=0x35, abs=0x2D, abs_x=0x3D, abs_y=0x39, ind_x=0x21, ind_y=0x31),
    'ASL': Opcode(implied=0x0A, zp=0x06, zp_x=0x16, abs=0x0E, abs_x=0x1E),
    'EOR': Opcode(imm=0x49, zp=0x45, zp_x=0x55, abs=0x4D, abs_x=0x5D, abs_y=0x59, ind_x=0x41, ind_y=0x51),
    'LSR': Opcode(implied=0x4A, zp=0x46, zp_x=0x56, abs=0x4E, abs_x=0x5E),
    'ORA': Opcode(imm=0x09, zp=0x05, zp_x=0x15, abs=0x0D, abs_x=0x1D, abs_y=0x19, ind_x=0x01, ind_y=0x11),
    'ROL': Opcode(implied=0x2A, zp=0x26, zp_x=0x36, abs=0x2E, abs_x=0x3E),
    'ROR': Opcode(implied=0x6A, zp=0x66, zp_x=0x76, abs=0x6E, abs_x=0x7E),
    'SBC': Opcode(imm=0xE9, zp=0xE5, zp_x=0xF5, abs=0xED, abs_x=0xFD, abs_y=0xF9, ind_x=0xE1, ind_y=0xF1),

    # Memory instructions
    'DEC': Opcode(zp=0xC6, zp_x=0xD6, abs=0xCE, abs_x=0xDE),
    'INC': Opcode(zp=0xE6, zp_x=0xF6, abs=0xEE, abs_x=0xFE),
    'LDA': Opcode(imm=0xA9, zp=0xA5, zp_x=0xB5, abs=0xAD, abs_x=0xBD, abs_y=0xB9, ind_x=0xA1, ind_y=0xB1),
    'LDX': Opcode(imm=0xA2, zp=0xA6, zp_y=0xB6, abs=0xAE, abs_y=0xBE),
    'LDY': Opcode(imm=0xA0, zp=0xA4, zp_x=0xB4, abs=0xAC, abs_x=0xBC),
    'STA': Opcode(zp=0x85, zp_x=0x95, abs=0x8D, abs_x=0x9D, abs_y=0x99, ind_x=0x81, ind_y=0x91),
    'STX': Opcode(zp=0x86, zp_y=0x96, abs=0x8E),
    'STY': Opcode(zp=0x84, zp_x=0x94, abs=0x8C),

    # Comparison instructions
    'BIT': Opcode(zp=0x24, abs=0x2C),
    'CMP': Opcode(imm=0xC9, zp=0xC5, zp_x=0xD5, abs=0xCD, abs_x=0xDD, abs_y=0xD9, ind_x=0xC1, ind_y=0xD1),
    'CPX': Opcode(imm=0xE0, zp=0xE4, abs=0xEC),
    'CPY': Opcode(imm=0xC0, zp=0xC4, abs=0xCC),

    # Branch instructions
    'BCC': Opcode(off=0x90),
    'BCS': Opcode(off=0xB0),
    'BEQ': Opcode(off=0xF0),
    'BMI': Opcode(off=0x30),
    'BNE': Opcode(off=0xD0),
    'BPL': Opcode(off=0x10),
    'BVC': Opcode(off=0x50),
    'BVS': Opcode(off=0x70),

    # Control flow instructions
    'JMP': Opcode(abs=0x4C, ind=0x6C),
    'JSR': Opcode(abs=0x20),
    'RTI': Opcode(0x40),
    'RTS': Opcode(0x60),

    # Register instructions
    'DEX': Opcode(0xCA),
    'DEY': Opcode(0x88),
    'INX': Opcode(0xE8),
    'INY': Opcode(0xC8),
    'TAX': Opcode(0xAA),
    'TAY': Opcode(0xA8),
    'TXA': Opcode(0x8A),
    'TYA': Opcode(0x98),

    # Stack instructions
    'PHA': Opcode(0x48),
    'PHP': Opcode(0x08),
    'PLA': Opcode(0x68),
    'PLP': Opcode(0x28),
    'TSX': Opcode(0xBA),
    'TXS': Opcode(0x9A),

    # Flag instructions
    'CLC': Opcode(0x18),
    'CLD': Opcode(0xD8),
    'CLI': Opcode(0x58),
    'CLV': Opcode(0xB8),
    'SEC': Opcode(0x38),
    'SED': Opcode(0xF8),
    'SEI': Opcode(0x78),

    # Misc instructions
    'BRK': Opcode(0x00),
    'NOP': Opcode(0xEA),
}


# Parse a line of ASM code
def parse_line(line):
    global prog_counter
    global current_file
    global current_line

    # Get the current file name and line number for error reporting
    current_file = file_name_stack[-1]
    current_line = line_count_stack[-1]

    instr_strings[(current_file, current_line)] = line
    tokens = token_regex.match(line.strip()).groups()

    if tokens:
        # Check if we have a label and add it to the label table
        if tokens[0]:
            name = tokens[0]
            if name not in label_table:
                label_table[name] = prog_counter
            else:
                error(current_file, current_line,
                      f'Label already exists "{name}"')

        # Check if we have an instruction
        if tokens[1]:
            instr_name = tokens[1].upper()
            param = tokens[2]

            if instr_name in opcode_table:
                # Parse as an opcode and operand
                instr = Instruction(instr_name, param)
                instruction_list.append(instr)
                prog_counter += instr.length

            elif instr_name in directive_table:
                # Parse as a directive
                try:
                    directive_table[instr_name](param)
                except TypeError:
                    error(current_file, current_line, 'Invalid parameter')
            else:
                error(current_file, current_line,
                      f'Invalid instruction "{tokens[1]}"')


# Parse an ASM code file
def parse_file(path):
    # Update the current file and line number for error reporting
    file_name_stack.append(path)
    line_count_stack.append(0)

    # Open the file and parse each line
    try:
        with open(path, 'r') as src_file:
            for line in src_file:
                line_count_stack[-1] += 1
                parse_line(line)
    except FileNotFoundError:
        error(current_file, current_line, f'Source file not found "{path}"')

    file_name_stack.pop()
    line_count_stack.pop()


if __name__ == '__main__':
    # Get command line arguments
    try:
        asm_file_name = sys.argv[1]
        out_file_name = sys.argv[2]
        debug_file_name = sys.argv[3] if len(sys.argv) > 3 else None
    except IndexError:
        print('usage: simple65.py <input_file> <output_file> [debug_file]')
        exit(-1)

    # Pass 1: Parse each line of ASM code into a list of instructions
    print('Pass 1...')
    parse_file(asm_file_name)

    # Pass 2: Evaluate each instruction or value into a list of bytes
    print('Pass 2...')
    rom_bytes = []
    debug_info = []

    for instr in instruction_list:
        # Get bytes for the current instruction
        bytes = instr.get_bytes()
        if any(b > 256 for b in bytes):
            error(instr.file, instr.line, 'Byte out of range')
        rom_bytes.extend(bytes)

        if debug_file_name is not None:
            # Generate debug info for the current instruction
            pos = len(rom_bytes) - len(bytes)
            key = (instr.file, instr.line)
            text = instr_strings[key].split(';')[0].strip()
            desc = instr.get_description()
            byte_string = ' '.join(f'{b:02X}' for b in bytes[:32])
            if len(bytes) > 32:
                byte_string += ' ...'
            debug_line = f'{pos:04X}:{instr.file}:{instr.line} "{text}" ({desc}) -> {byte_string}\n'
            debug_info.append(debug_line)

    # Write ROM bytes out to a file
    print(f'Writing {len(rom_bytes)} bytes to {out_file_name}')
    try:
        with open(out_file_name, 'wb') as rom_file:
            rom_file.write(bytearray(rom_bytes))
    except PermissionError:
        print('ERROR: Output file could not be opened')

    if debug_file_name is not None:
        # Write debug info out to a file
        print(f'Writing debug output to {debug_file_name}')
        try:
            with open(debug_file_name, 'w') as debug_file:
                debug_file.writelines(debug_info)
        except PermissionError:
            print('ERROR: Debug file could not be opened')
