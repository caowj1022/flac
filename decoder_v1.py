import struct, sys
import argparse

# Class to store metadata
class MetaData(object):

	def __init__(self):
		self.minimum_block_size = 0
		self.maximum_block_size = 0
		self.minimum_frame_size = 0
		self.maximum_frame_size = 0
		self.sample_rate = 0
		self.number_of_channels = 0
		self.bits_per_sample = 0
		self.total_samples = 0

	def print_metadata(self):

		print "Minimun block size:", self.minimum_block_size
		print "Maximum block size:", self.maximum_block_size
		print "Minimun frame size:", self.minimum_frame_size
		print "Maximum frame size:", self.maximum_frame_size
		print "Sample rate:", self.sample_rate
		print "Number of channels:", self.number_of_channels
		print "Bits per sample:", self.bits_per_sample
		print "total_samples:", self.total_samples

metadata = MetaData()

# Class to handle file write operation
class FileWrite(object):
	def __init__(self, file_out):
		self.file_out = file_out

	def write_int_little(self, n):
		self.file_out.write(struct.pack("<I", n))

	def write_short_little(self, n):
		self.file_out.write(struct.pack("<H", n))

	def write_int_big(self, n):
		self.file_out.write(struct.pack(">I", n))

	def write_short_big(self, n):
		self.file_out.write(struct.pack(">H", n))

	def write_nbytes_little(self, nbytes, n):
		for i in range(nbytes):
			self.file_out.write(chr((n >> (i * 8)) & 0xFF))

# Class to handle file read
class FileRead(object):
	
	def __init__(self, file_in):
		self.file_in = file_in

		# Buffer for bits operation
		self.buffer = 0
		self.buffer_len = 0
	
	# Read a byte
	def read_byte(self):
		if self.buffer_len >= 8:
			return self.read_bits_unsigned(8)
		else:
			ret = self.file_in.read(1)
			if len(ret) == 0:
				return -1
			return ord(ret)
	
	# Read n bits as an unsinged integer
	def read_bits_unsigned(self, n):
		while self.buffer_len < n:
			temp = self.file_in.read(1)
			if len(temp) == 0:
				raise EOFError()
			self.buffer = (self.buffer << 8) | (ord(temp))
			self.buffer_len += 8
		self.buffer_len -= n
		ret = (self.buffer >> self.buffer_len) & ((1 << n) - 1)
		self.buffer &= (1 << self.buffer_len) - 1
		return ret
	
	# Read n bits as signed integer
	# Two's complement
	def read_bits_signed(self, n):
		ret = self.read_bits_unsigned(n)
		ret -= (ret >> (n - 1)) << n
		return ret


	def read_rice(self, parameter):	
		msb = 0
		while self.read_bits_unsigned(1) == 0:
			msb += 1
		lsb = self.read_bits_unsigned(parameter)
#		print "msb", msb
#		print "lsb", lsb
#		results = (msb << (parameter - 1)) | (lsb >> 1)
#		results = results ^ (-(lsb & 0x1))
		results = (msb << parameter) | lsb
		results = (results >> 1) ^ (-(results & 0x1))
		return results

	def byte_alignment(self):
		self.buffer_len = self.buffer_len - self.buffer_len % 8

def generate_parser():
	parser = argparse.ArgumentParser(description =  "This program is to taks a .flac file as input, decode it and output a .wav file")
	parser.add_argument('flac_in', help = "Input .flac file")
	parser.add_argument('wav_out', help = "Output wav file")

	return parser
def main(argv):
#	if len(argv) != 3:
#		sys.exit("Invalid input format, input.flac output.wav")

	parser = generate_parser()
	args = parser.parse_args()


	file1 = open(args.flac_in, "rb")
	file_in = FileRead(file1)
	file2 = open(args.wav_out, "wb")
	file_out = FileWrite(file2)
	decode_stream(file_in, file_out)

# Decode stream
def decode_stream(file_in, file_out):

	if file_in.read_bits_unsigned(32) != 0x664C6143:
		sys.exit("Invalid flac file")

	while(not decode_metadata_block(file_in)):
		pass

	global metadata
	metadata.print_metadata()

	write_wav_header(file_out)

	while decode_frame(file_in, file_out):
		pass

# Decode metadata block
# If block tyoe is stream infomation block, read stream information
def decode_metadata_block(file_in):

	global metadata

	ret = file_in.read_bits_unsigned(1)
	block_type = file_in.read_bits_unsigned(7)
	metadata_length = file_in.read_bits_unsigned(24)
	if block_type == 0:
		metadata.minimum_block_size = file_in.read_bits_unsigned(16)
		metadata.maximum_block_size = file_in.read_bits_unsigned(16)
		metadata.minimum_frame_size = file_in.read_bits_unsigned(24)
		metadata.maximum_frame_size = file_in.read_bits_unsigned(24)
		metadata.sample_rate = file_in.read_bits_unsigned(20)
		metadata.number_of_channels = file_in.read_bits_unsigned(3) + 1
		metadata.bits_per_sample = file_in.read_bits_unsigned(5) + 1
		metadata.total_samples = file_in.read_bits_unsigned(36)
		file_in.read_bits_unsigned(128)
	elif 1 <= block_type <= 6:
		for i in range(metadata_length):
			file_in.read_bits_unsigned(8)
	elif 7 <= block_type <= 126:
		sys.exit("Error, block_type is reserved")
	else:
		sys.exit("Error, block_type is invalid")
	return ret

# Write Wav file header
def write_wav_header(file_out):

	global metadata
	file_out.write_int_big(0x52494646)
	data_size = metadata.total_samples * metadata.number_of_channels * (metadata.bits_per_sample // 8)
	file_out.write_int_little(data_size + 36)
	file_out.write_int_big(0x57415645)
	file_out.write_int_big(0x666D7420)
	file_out.write_int_little(16)
	file_out.write_short_little(0x0001)
	file_out.write_short_little(metadata.number_of_channels)
	file_out.write_int_little(metadata.sample_rate)
	file_out.write_int_little(metadata.sample_rate * metadata.bits_per_sample * metadata.number_of_channels // 8)
	file_out.write_short_little(metadata.bits_per_sample * metadata.number_of_channels // 8)
	file_out.write_short_little(metadata.bits_per_sample)
	file_out.write_int_big(0x64617461)
	file_out.write_int_little(data_size)

# decode a frame
def decode_frame(file_in, file_out):
	
	global metadata

	temp = file_in.read_byte()
	if temp == -1:
		print "All bits read"
		return False
	temp = temp << 6 | file_in.read_bits_unsigned(6)
	if temp != 0x3FFE:
		print "syn code:", temp
		sys.exit("Error Syn Code")

	if file_in.read_bits_unsigned(1) == 1:
		sys.exit("Reserve bit")

	blocking_strategy = file_in.read_bits_unsigned(1)
	block_size_code = file_in.read_bits_unsigned(4)
	sample_rate_code = file_in.read_bits_unsigned(4)
	channel_assignment = file_in.read_bits_unsigned(4)
	bits_per_sample_code = file_in.read_bits_unsigned(3)

	if bits_per_sample_code == 0:
		bits_per_sample = metadata.bits_per_sample
	elif bits_per_sample_code == 1:
		bits_per_sample = 8
	elif bits_per_sample_code == 2:
		bits_per_sample = 12
	elif bits_per_sample_code == 3:
		sys.exix("Reserve sample size")
	elif bits_per_sample_code == 4:
		bits_per_sample = 16
	elif bits_per_sample_code == 5:
		bits_per_sample = 20
	elif bits_per_sample_code == 6:
		bits_per_sample = 24
	elif bits_per_sample_code == 7:
		sys.exit("Reserve sample size")

	if file_in.read_bits_unsigned(1) == 1:
		sys.exit("Reserve bit")
	
	temp = file_in.read_bits_unsigned(8)
	while temp >= 0xC0:
		file_in.read_bits_unsigned(8)
		temp = (temp << 1) & 0xFF
	
	if block_size_code == 0:
		sys.exit("Reserve block size code")
	elif block_size_code == 1:
		block_size = 192
	elif 2 <= block_size_code <= 5:
		block_size = 576 << (block_size_code - 2)
	elif block_size_code == 6:
		block_size = file_in.read_bits_unsigned(8) + 1
	elif block_size_code == 7:
		block_size = file_in.read_bits_unsigned(16) + 1
	elif 8 <= block_size_code <= 15:
		block_size = 256 << (block_size_code - 8)
	
	if sample_rate_code == 12:
		file_in.read_bits_unsigned(8)
	elif 13 <= sample_rate_code <= 14:
		file_in.read_bits_unsigned(16)
	elif sample_rate_code == 15:
		sys.exit("Invalid sample rate code")
	
	file_in.read_bits_unsigned(8)
	
	if 0 <= channel_assignment <= 7:
		results = [decode_subframe(file_in, block_size, bits_per_sample) for _ in range(channel_assignment + 1)]
	elif 8 <= channel_assignment <= 10:
		channel0 = decode_subframe(file_in, block_size, bits_per_sample + (1 if (channel_assignment == 9) else 0))
		channel1 = decode_subframe(file_in, block_size, bits_per_sample + (0 if (channel_assignment == 9) else 1))

		if channel_assignment == 8:
			for i in range(block_size):
				channel1[i] = channel0[i] - channel1[i]
		elif channel_assignment == 9:
			for i in range(block_size):
				channel0[i] = channel0[i] + channel1[i]
		else:
			for i in range(block_size):
				channel0[i] = (2 * channel0[i] + channel1[i]) / 2
				channel1[i] = (2 * channel0[i] - channel1[i]) / 2
		results = [channel0, channel1]
	else:
		sys.exit("Reserve channel_assignment")

	file_in.byte_alignment()
	file_in.read_bits_unsigned(16)

	bytes_per_sample = bits_per_sample // 8

	padding = 0
	if bits_per_sample == 8:
		padding = 128

	for i in range(block_size):
		for j in range(metadata.number_of_channels):
			file_out.write_nbytes_little(bytes_per_sample, results[j][i] + padding)
	return True


def decode_subframe(file_in, block_size, bits_per_sample):

	file_in.read_bits_unsigned(1)
	subframe_type = file_in.read_bits_unsigned(6)
	wasted_bits_per_sample = file_in.read_bits_unsigned(1)
	if wasted_bits_per_sample == 1:
		while file_in.read_bits_unsigned(1) == 0:
			wasted_bits_per_sample += 1
	
	if subframe_type == 0:
		results = [file_in.read_bits_signed(bits_per_sample)] * block_size
	elif subframe_type == 1:
		results = [file_in.read_bits_signed(bits_per_sample) for _ in range(block_size)]
	elif 8 <= subframe_type <= 12:
		results = decode_subframe_fixed(file_in, subframe_type - 8, block_size, bits_per_sample)
	elif 32 <= subframe_type <= 63:
		results = decode_subframe_LPC(file_in, subframe_type - 31, block_size, bits_per_sample)
	else:
		sys.exit("Reserve subframe type")

	for i in range(len(results)):
		results[i] = results[i] << wasted_bits_per_sample
	return results

def decode_subframe_fixed(file_in, order, block_size, bits_per_sample):

	results = [file_in.read_bits_signed(bits_per_sample) for _ in range(order)]
	decode_residuals(file_in, block_size, results)

	if order == 0:
		pass
	elif order == 1:
		for i in range(1, len(results)):
			results[i] += results[i-1]
	elif order == 2:
		for i in range(2, len(results)):
			results[i] = 2 * results[i-1] - results[i-2] + results[i]
	elif order == 3:
		for i in range(3, len(results)):
			results[i] = 3 * results[i-1] - 3 * results[i-2] + results[i-3] + results[i]
	elif order == 4:
		for i in range(4, len(results)):
			results[i] = 4 * results[i-1] -6 * results[i-2] + 4 * results[i-3] -results[i-4] + results[i]
	else:
		print order
		sys.exit("Invalid subframe fixed order")
	return results

def decode_residuals(file_in, block_size, results):

	residuals_method = file_in.read_bits_unsigned(2)

	if residuals_method >= 2:
		sys.exit("Reserve residuals method")
	elif residuals_method == 0:
		parameter_bits = 4
		escape_code = 0xF
	else:
		parameter_bits = 5
		escape_code = 0x1F
	
	partition_order = file_in.read_bits_unsigned(4)
	number_of_partitions = 1 << partition_order

	for i in range(number_of_partitions):
		number_samples = block_size >> partition_order
		if i == 0:
			number_samples -= len(results)

		parameter = file_in.read_bits_unsigned(parameter_bits)
		if parameter < escape_code:
			results.extend(file_in.read_rice(parameter) for _ in range(number_samples))
		else:
			bits = file_in.read_bits_unsigned(5)
			results.extend(file_in.read_bits_signed(bits) for _ in range(number_samples))


def decode_subframe_LPC(file_in, order, block_size, bits_per_sample):

	results = [file_in.read_bits_signed(bits_per_sample) for _ in range(order)]

	coefficient_bits = file_in.read_bits_unsigned(4) + 1
	shift_needed = file_in.read_bits_unsigned(5)
	coefficient = [file_in.read_bits_signed(coefficient_bits) for _ in range(order)]

	decode_residuals(file_in, block_size, results)

	for i in range(order, block_size):
		temp = 0
		for j in range(order):
			temp = temp + coefficient[j] * results[i-j-1]
		temp = temp >> shift_needed
		results[i] = results[i] + temp
	return results

if __name__ == "__main__":
	main(sys.argv)