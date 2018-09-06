#!/usr/bin/env python3


import sys, re
from collections import Counter


class Label:

	def __init__(self, value = None):

		self.value = value
		self.high_refs = []
		self.low_refs = []
		self.off_refs = []
		self.off_pc = []


	def backfill_references(self):

		# replace label references with real values
		for href in self.high_refs:
			rom_bytes[href] = self.value & 0xF0
		for lref in self.low_refs:
			rom_bytes[lref] = self.value & 0x0F
		for oref, opc in zip(self.off_refs, self.off_pc):
			rom_bytes[oref] = self.value - opc


class Opcode:

	def __init__(self, implied = None, acc = None, imm = None, zp = None, zp_x = None, zp_y = None, abs = None, abs_x = None, abs_y = None, ind = None, ind_x = None, ind_y = None, off = None):

		self.implied = implied if implied else acc
		self.acc = acc
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


label_table = {}

opcode_table = {

	# Math instructions
	'ADC': Opcode(imm = 0x69, zp = 0x65, zp_x = 0x75, abs = 0x6D, abs_x = 0x7D, abs_y = 0x79, ind_x = 0x61, ind_y = 0x71),
	'AND': Opcode(imm = 0x29, zp = 0x25, zp_x = 0x35, abs = 0x2D, abs_x = 0x3D, abs_y = 0x39, ind_x = 0x21, ind_y = 0x31),
	'ASL': Opcode(acc = 0x0A, zp = 0x06, zp_x = 0x16, abs = 0x0E, abs_x = 0x1E),
	'EOR': Opcode(imm = 0x49, zp = 0x45, zp_x = 0x55, abs = 0x4D, abs_x = 0x5D, abs_y = 0x59, ind_x = 0x41, ind_y = 0x51),
	'LSR': Opcode(acc = 0x4A, zp = 0x46, zp_x = 0x56, abs = 0x4E, abs_x = 0x5E),
	'ORA': Opcode(imm = 0x09, zp = 0x05, zp_x = 0x15, abs = 0x0D, abs_x = 0x1D, abs_y = 0x19, ind_x = 0x01, ind_y = 0x11),
	'ROL': Opcode(acc = 0x2A, zp = 0x26, zp_x = 0x36, abs = 0x2E, abs_x = 0x3E),
	'ROR': Opcode(acc = 0x6A, zp = 0x66, zp_x = 0x76, abs = 0x6E, abs_x = 0x7E),
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


token_regex = re.compile('(?:(^[A-Za-z_]\w*):)?\s*([\.\w]+)?(?:\s+(.+)$)?')
param_regex = re.compile('"[^"]+"|;.*$|[^\s,]+')

prog_counter = 0
rom_bytes = []


def parse_value(param):

	# Parse a value
	if param[0] == '$':
		return int(param[1:], 16)
	elif param[0] == '%':
		return int(param[1:], 2)
	elif param.isdigit():
		return int(param)
	else:
		return param


def parse_line(line):

	tokens = token_regex.match(line.strip()).groups()

	# Check if we have a label
	if tokens[0]:
		name = tokens[0]
		if name in label_table:
			error('Label already defined: %s' % name)
		else:
			label_table[name] = Label(prog_counter)

	# Check if we have an instruction
	if tokens[1]:
		instruction = tokens[1]
		params = [parse_param(param) for param in param_regex.findall(tokens[2].strip()) if param and param[0] != ';'] if tokens[2] else None
		if instruction in opcode_table:
			print('opcde:\t%s, %s' % (instruction, params))
		else:
			print('drctv:\t%s, %s' % (instruction, params))


if __name__ == '__main__':

	with open(sys.argv[1], 'r') as src_file:
		for line in src_file:
			parse_line(line)
