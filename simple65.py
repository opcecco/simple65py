#!/usr/bin/env python3


import sys, re
import pprint


token_regex = re.compile('(?:([A-Za-z_]\w*):)?(?:\s*([\.\w]+))?(?:\s+([^;]+[^;\s]))?(?:\s*(;.*))?')
operand_regex = re.compile('([#\(])?([<>$%\w]+)(\))?(?:,\s*([XxYy]))?(\))?')
value_regex = re.compile('([<>])?([%$])?(\w+)')
param_split_regex = re.compile(',\s*')


class Opcode:

	def __init__(self, implied = None, imm = None, zp = None, zp_x = None, zp_y = None, abs = None, abs_x = None, abs_y = None, ind = None, ind_x = None, ind_y = None, off = None):

		self.length = 1
		self.byte = {
			'implied': implied,
			'imm':     imm,
			'zp':      zp,
			'zp_x':    zp_x,
			'zp_y':    zp_y,
			'abs':     abs,
			'abs_x':   abs_x,
			'abs_y':   abs_y,
			'ind':     ind,
			'ind_x':   ind_x,
			'ind_y':   ind_y,
			'off':     off,
		}


class Operand:

	mode_dict = {
		('#',  None, None, None, 1): 'imm',
		(None, None, None, None, 1): 'zp',
		(None, None, 'X',  None, 1): 'zp_x',
		(None, None, 'Y',  None, 1): 'zp_y',
		(None, None, None, None, 2): 'abs',
		(None, None, 'X',  None, 2): 'abs_x',
		(None, None, 'Y',  None, 2): 'abs_y',
		('(',  ')',  None, None, 2): 'ind',
		('(',  None, 'X',  ')',  1): 'ind_x',
		('(',  ')',  'Y',  None, 1): 'ind_y',
	}


	def __init__(self, oper_str, offset = False):

		self.pc = prog_counter

		if oper_str:
			tokens = operand_regex.match(oper_str).groups()
			self.value = Value(tokens[1])

			if offset:
				self.length = 1
				self.mode = 'off'
			else:
				self.length = self.value.length
				mode_key = (tokens[0], tokens[2], tokens[3].upper() if tokens[3] else None, tokens[4], self.value.length)
				self.mode = Operand.mode_dict[mode_key]

		else:
			self.value = None
			self.length = 0
			self.mode = 'implied'


	def get_bytes(self):

		if self.mode == 'implied':
			return ()
		elif self.mode == 'off':
			return (self.value.get_bytes()[0] & 0x0F,)
		else:
			return self.value.get_bytes()


	def __repr__(self):

		return str((self.mode, self.value,))


class Value:

	def __init__(self, val_str):

		tokens = value_regex.match(val_str).groups()
		self.truncation = 1 if tokens[0] == '>' else -1 if tokens[0] == '<' else 0
		base = 16 if tokens[1] == '$' else 2 if tokens[1] == '%' else 10 if tokens[2].isdigit() else None
		self.literal = int(tokens[2], base) if base is not None else None
		self.label = tokens[2] if self.literal is None else None
		self.length = 1 if self.truncation != 0 or (self.literal is not None and self.literal < 256) else 2


	def get_bytes(self):

		out_val = self.literal if self.literal is not None else label_table[self.label]

		if self.truncation == -1:
			out_val &= 0xFF
		elif self.truncation == 1:
			out_val >>= 8

		if self.length == 1:
			return [out_val]
		else:
			return [out_val & 0xFF, out_val >> 8]


	def __repr__(self):

		return str(vars(self))


class Instruction:

	def __init__(self, opcode_str, operand_str):

		self.opcode_str = opcode_str
		self.opcode = opcode_table[opcode_str]
		self.operand = Operand(operand_str, offset = self.opcode.byte['off'])
		self.length = self.opcode.length + self.operand.length


	def get_bytes(self):

		out_bytes = [self.opcode.byte[self.operand.mode]]
		out_bytes.extend(self.operand.get_bytes())
		return out_bytes


	def __repr__(self):

		return str((self.opcode_str, self.operand,))


opcode_table = {

	# Math instructions
	'ADC': Opcode(imm = 0x69, zp = 0x65, zp_x = 0x75, abs = 0x6D, abs_x = 0x7D, abs_y = 0x79, ind_x = 0x61, ind_y = 0x71),
	'AND': Opcode(imm = 0x29, zp = 0x25, zp_x = 0x35, abs = 0x2D, abs_x = 0x3D, abs_y = 0x39, ind_x = 0x21, ind_y = 0x31),
	'ASL': Opcode(implied = 0x0A, zp = 0x06, zp_x = 0x16, abs = 0x0E, abs_x = 0x1E),
	'EOR': Opcode(imm = 0x49, zp = 0x45, zp_x = 0x55, abs = 0x4D, abs_x = 0x5D, abs_y = 0x59, ind_x = 0x41, ind_y = 0x51),
	'LSR': Opcode(implied = 0x4A, zp = 0x46, zp_x = 0x56, abs = 0x4E, abs_x = 0x5E),
	'ORA': Opcode(imm = 0x09, zp = 0x05, zp_x = 0x15, abs = 0x0D, abs_x = 0x1D, abs_y = 0x19, ind_x = 0x01, ind_y = 0x11),
	'ROL': Opcode(implied = 0x2A, zp = 0x26, zp_x = 0x36, abs = 0x2E, abs_x = 0x3E),
	'ROR': Opcode(implied = 0x6A, zp = 0x66, zp_x = 0x76, abs = 0x6E, abs_x = 0x7E),
	'SBC': Opcode(imm = 0xE9, zp = 0xE5, zp_x = 0xF5, abs = 0xED, abs_x = 0xFD, abs_y = 0xF9, ind_x = 0xE1, ind_y = 0xF1),

	# Memory instructions
	'DEC': Opcode(zp = 0xC6, zp_x = 0xD6, abs = 0xCE, abs_x = 0xDE),
	'INC': Opcode(zp = 0xE6, zp_x = 0xF6, abs = 0xEE, abs_x = 0xFE),
	'LDA': Opcode(imm = 0xA9, zp = 0xA5, zp_x = 0xB5, abs = 0xAD, abs_x = 0xBD, abs_y = 0xB9, ind_x = 0xA1, ind_y = 0xB1),
	'LDX': Opcode(imm = 0xA2, zp = 0xA6, zp_y = 0xB6, abs = 0xAE, abs_y = 0xBE),
	'LDY': Opcode(imm = 0xA0, zp = 0xA4, zp_x = 0xB4, abs = 0xAC, abs_x = 0xBC),
	'STA': Opcode(zp = 0x85, zp_x = 0x95, abs = 0x8D, abs_x = 0x9D, abs_y = 0x99, ind_x = 0x81, ind_y = 0x91),
	'STX': Opcode(zp = 0x86, zp_y = 0x96, abs = 0x8E),
	'STY': Opcode(zp = 0x84, zp_x = 0x94, abs = 0x8C),

	# Comparison instructions
	'BIT': Opcode(zp = 0x24, abs = 0x2C),
	'CMP': Opcode(imm = 0xC9, zp = 0xC5, zp_x = 0xD5, abs = 0xCD, abs_x = 0xDD, abs_y = 0xD9, ind_x = 0xC1, ind_y = 0xD1),
	'CPX': Opcode(imm = 0xE0, zp = 0xE4, abs = 0xEC),
	'CPY': Opcode(imm = 0xC0, zp = 0xC4, abs = 0xCC),

	# Branch instructions
	'BCC': Opcode(off = 0x90),
	'BCS': Opcode(off = 0xB0),
	'BEQ': Opcode(off = 0xF0),
	'BMI': Opcode(off = 0x30),
	'BNE': Opcode(off = 0xD0),
	'BPL': Opcode(off = 0x10),
	'BVC': Opcode(off = 0x50),
	'BVS': Opcode(off = 0x70),

	# Control flow instructions
	'JMP': Opcode(abs = 0x4C, ind = 0x6C),
	'JSR': Opcode(abs = 0x20),
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


label_table = {}
instruction_list = []
prog_counter = 0
current_line = 0


def parse_line(line):

	global current_line
	global prog_counter

	current_line += 1
	tokens = token_regex.match(line.strip()).groups()

	if tokens:

		if tokens[0]:
			name = tokens[0]
			label_table[name] = prog_counter

		if tokens[1]:
			opcode = tokens[1].upper()
			operand = tokens[2]
			instr = Instruction(opcode, operand)
			instruction_list.append(instr)
			prog_counter += instr.length


if __name__ == '__main__':

	with open(sys.argv[1], 'r') as src_file:
		for line in src_file:
			try:
				parse_line(line)
			except:
				print('Error: line %d' % current_line)
				raise

	pprint.pprint(instruction_list)
	pprint.pprint(['%s: %X' % (name, label_table[name]) for name in label_table])

	rom_bytes = []
	for instr in instruction_list:
		rom_bytes.extend(instr.get_bytes())

	pprint.pprint(['%04X: %02X' % (i, byte) for i, byte in enumerate(rom_bytes)])

	with open(sys.argv[2], 'wb') as rom_file:
		rom_file.write(bytearray(rom_bytes))
