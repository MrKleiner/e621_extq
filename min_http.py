import socket, threading, io, time, json
from urllib.parse import unquote
import urllib

"""
Minimal HTTP server
"""


class MinHTTPRequest:
	def __init__(self, hlist, cl_con, shared_data=None):
		self.shared_data = shared_data
		self.cl_con = cl_con
		self.hlist = hlist
		self.method, self.path, self.protocol = self.hlist[0].split(' ')
		del self.hlist[0]

		parsed_url = urllib.parse.urlparse(self.path)

		self.query_params:dict = {k:(''.join(v)) for (k,v) in urllib.parse.parse_qs(parsed_url.query, True).items()}

		self.path = urllib.parse.unquote(parsed_url.path)

		self.headers = {}

		for header in self.hlist:
			hkey, hval = header.split(': ')
			self.headers[hkey.strip()] = hval.strip()


	def send_headers(self, hdict):
		for hkey, hval in hdict.items():
			self.cl_con.sendall(f"""{str(hkey)}: {str(hval)}\r\n""".encode())


	def flush_bytes(self, data, content_type='text/plain'):
		self.cl_con.sendall('HTTP/1.1 200 OK\r\n'.encode())
		self.send_headers(
			{
				'Server': 'e621_extq',
				'Content-Type': str(content_type),
				'Connection': 'Keep-Alive',
				'Content-Length': len(data),
			}
		)
		self.cl_con.sendall(b'\r\n')
		self.cl_con.sendall(data)


	def flush_json(self, data):
		self.flush_bytes(
			json.dumps(data).encode(),
			'application/json'
		)


class MinHTTP:
	def __init__(self, callback, shared_data=None, tgt_port=None):
		self.callback = callback
		self.shared_data = shared_data
		self.addr_info = None
		threading.Thread(target=self.serve, args=(tgt_port,)).start()


	def collect_headers(self, cl_con):
		skt_file = cl_con.makefile('rb', newline=b'\r\n', buffering=0)
		hlist = []

		while True:
			line = skt_file.readline()

			if not line or line == b'\r\n':
				break

			hlist.append(line.decode().strip())

		skt_file.close()

		return hlist


	def htsession(self, cl_con):
		while True:
			headers = self.collect_headers(cl_con)
			if not headers:
				return

			http_request = MinHTTPRequest(headers, cl_con, self.shared_data)

			self.callback(http_request)


	def serve(self, tgt_port=None):
		skt = socket.socket()
		skt.bind(
			# ('', 8089)
			('', tgt_port or 0)
		)
		skt.listen(0)
		self.addr_info = skt.getsockname()
		while True:
			conn, address = skt.accept()
			threading.Thread(
				target=self.htsession,
				args=(conn,)
			).start()





