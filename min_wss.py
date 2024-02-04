import hashlib, base64, struct, io, collections, json


def clamp_num(num, tgt_min, tgt_max):
	return max(tgt_min, min(num, tgt_max))




class WSSMask:
	def __init__(self, mask_bytes):
		self.bytes_static = mask_bytes
		self.bytes = collections.deque(list(mask_bytes))

	def unmask(self, data, mask):
		bt_array = bytearray(data)
		for idx in range(len(bt_array)):
			bt_array[idx] ^= mask[idx % 4]

		return bytes(bt_array)


	def apply(self, data):
		xored = self.unmask(data, bytes(self.bytes))
		self.bytes.rotate(len(data))
		return xored



class MinWSession:
	def __init__(self, cl_con):
		self.cl_con = cl_con
		try:
			self.resolve_handshake()
		except Exception as e:
			print(e)
		

	# aligned_receive
	def aligned_recv(self, bufsize, chunk_size=8192):
		# Shouldn't this print a warning or something ?
		if bufsize <= 0:
			return b''

		# Creating an io.BytesIO buffer to receive 2 bytes
		# is MUCH slower than simple concatenating (b'' + ...)
		# Through tests it was determined that there's no need to
		# create a buffer for receiving less than 512 bytes.
		# todo: Lower the number a little bit just to be sure?
		if bufsize < 512:
			buf = b''
			# print('Need to receive:', bufsize)
			while True:
				# todo: raise a warning when the result is actually longer
				# than anticipated
				if len(buf) >= bufsize:
					return buf

				data = self.cl_con.recv(
					clamp_num(chunk_size, 1, bufsize - len(buf))
				)
				buf += data
		else:
			buf = self.io.BytesIO()
			while True:
				if buf.tell() >= bufsize:
					return buf.getvalue()

				data = self.cl_con.recv(
					clamp_num(chunk_size, 1, bufsize - buf.tell())
				)
				buf.write(data)

		return buf


	def resolve_handshake(self):
		skt_file = self.cl_con.makefile('rb', newline=b'\r\n', buffering=0)
		hlist = []
		while True:
			line = skt_file.readline()
			if not line or line == b'\r\n':
				break
			hlist.append(line.decode().strip())
		skt_file.close()

		hshake_info = {}
		for ln in hlist:
			splitline = ln.split(': ')
			hshake_info[splitline[0].strip().lower()] = ': '.join(splitline[1:]).strip()

		# construct a response
		resolve = {
			'Upgrade': 'websocket',
			'Connection': 'Upgrade',
		}

		if 'sec-websocket-key' in hshake_info:
			self.input_wss_key = hshake_info['sec-websocket-key']
			self.output_wss_key = hashlib.sha1(
				(hshake_info['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()
			)
			# important todo: is this magic string actually important ?
			# aka could it be any other string ?
			resolve['Sec-WebSocket-Accept'] = base64.b64encode(self.output_wss_key.digest()).decode()

		self.cl_con.sendall(b'HTTP/1.1 101 Switching Protocols\r\n')
		for key in resolve:
			self.cl_con.sendall(f"""{key}: {resolve[key]}\r\n""".encode())
		self.cl_con.sendall(b'\r\n')


	def eval_length(self, data, strip_mask=True):
		"""
		Evaluate payload length from received bytes.
		- data:bytes|int
			- bytes: Evaluate int FROM bytes
					 Unpacking size is determined automatically
					 from the amount of bytes passed.
			- int: Evaluate int TO bytes
		- strip_mask:bool
			Strip first bit of the data.
			Only works if data is isntance of int
		"""
		length = None
		if isinstance(data, bytes):
			if len(data) == 1:
				data_unpack = struct.unpack('!B', data)[0]
				if strip_mask:
					data_unpack = data_unpack & 0b01111111
				length = data_unpack
			if len(data) == 2:
				length = struct.unpack('!H', data)[0]
			if len(data) == 3:
				length = struct.unpack('!Q', data)[0]

			return length

		if isinstance(data, int):
			if strip_mask:
				data = data & 0b01111111
			return data


	# Receive a message
	def recv_message(self):
		msg_buf = io.BytesIO()

		while True:
			hbytes = self.aligned_recv(2)

			hbyte1 = hbytes[0:1]
			hbyte2 = hbytes[1:2]

			# print('Received 2 header bytes:', hbytes, hbyte1, hbyte2)
			bits1 = struct.unpack('!B', hbyte1)[0]
			bits2 = struct.unpack('!B', hbyte2)[0]

			fin =    True if bits1 & 0b10000000 else False
			rsv1 =   True if bits1 & 0b01000000 else False
			rsv2 =   True if bits1 & 0b00100000 else False
			rsv3 =   True if bits1 & 0b00010000 else False
			opcode = bits1 & 0b00001111

			masked = True if bits2 & 0b10000000 else False

			frame_len = self.eval_length(hbyte2)

			if frame_len == 126:
				frame_len = self.eval_length(self.aligned_recv(2))
			elif frame_len == 127:
				frame_len = self.eval_length(self.aligned_recv(8))

			if masked:
				wss_mask = WSSMask(self.aligned_recv(4))

			if masked:
				msg_buf.write(
					wss_mask.apply(self.aligned_recv(frame_len))
				)
			else:
				msg_buf.write(self.aligned_recv(frame_len))

			if fin:
				break

		return msg_buf.getvalue()


	def send_message(self, data):
		data_len = len(data)
		head1 = (
			# FIN bit. 1 = fin, 0 = continue
			   0b10000000
			# Useless shit (poor documentation + not supported by browsers)
			| (0b01000000 if False else 0)
			| (0b00100000 if False else 0)
			| (0b00010000 if False else 0)
			# The opcode of the first frame in a sequence of fragmented frames
			# has to specify the type of the sequence (bytes/text/ping)
			# whereas all the following fragmented frames should have an opcode of 0x0
			# (final frame is marked with the fin bit)
			| 0x2
		)

		head2 = 0b10000000 if False else 0b00000000

		if data_len < 126:
			header = struct.pack('!BB', head1, head2 | data_len)
		elif data_len < 65536:
			header = struct.pack('!BBH', head1, head2 | 126, data_len)
		else:
			header = struct.pack('!BBQ', head1, head2 | 127, data_len)

		self.cl_con.sendall(header)
		self.cl_con.sendall(data)


	def send_json(self, data):
		self.send_message(json.dumps(data).encode())
