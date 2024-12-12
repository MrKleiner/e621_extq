from pathlib import Path
from datetime import datetime

import time
import multiprocessing
import threading
import secrets
import io
import math
import os
import pickle
import importlib
import requests
import gzip
import shutil
import csv

from bs4 import BeautifulSoup as jquery



# Points to the directory this script is located in
THISDIR = Path(__file__).parent



# --------------
#   Constants
# --------------

# Path pointing to a directory containing files which are basically caches:
# - Download caches (if any)
# - Last session save
# - Cooked DB
# .lzrd files are pickled python objects
CACHE_DIR = THISDIR / 'data'

# Gzipped csv file, which containes the entire DB
DB_GZIP_CACHE_FPATH = CACHE_DIR / 'db_data_full_compressed.csv.gz'

# Gzipped csv file, which contains the entirety of tags
TAGS_GZIP_CACHE_FPATH = CACHE_DIR / 'tags_all_compressed.csv.gz'

# Url pointing to an HTML page with DB exports download links
DB_DL_BASE_URL = 'https://e621.net/db_export/'

# Filepath pointing to a cooked DB
COOKED_DB_FPATH = CACHE_DIR / 'db_cooked.lzrd'

# Filepath pointing to a cooked DB
COOKED_TAGS_FPATH = CACHE_DIR / 'tags_cooked.lzrd'

# Filepath pointing to the last session save file
GAMESAVE_FPATH = CACHE_DIR / 'gamesave.lzrd'

# Character used to separate DB columns
SEP_CHAR = '\0'

# DB column field names and their indices
DB_STRUCT = (
	'id',                # 0
	'uploader_id',       # 1
	'created_at',        # 2
	'md5',               # 3
	'source',            # 4
	'rating',            # 5
	'image_width',       # 6
	'image_height',      # 7
	'tag_string',        # 8
	'locked_tags',       # 9
	'fav_count',         # 10
	'file_ext',          # 11
	'parent_id',         # 12
	'change_seq',        # 13
	'approver_id',       # 14
	'file_size',         # 15
	'comment_count',     # 16
	'description',       # 17
	'duration',          # 18
	'updated_at',        # 19
	'is_deleted',        # 20
	'is_pending',        # 21
	'is_flagged',        # 22
	'score',             # 23
	'up_score',          # 24
	'down_score',        # 25
	'is_rating_locked',  # 26
	'is_status_locked',  # 27
	'is_note_locked',    # 28
)

# Specifies which columns to keep. All the other ones will be emptied
DB_STRUCT_PASS = (
	0,  # id
	2,  # created_at
	3,  # md5
	5,  # rating
	8,  # tag_string
	11, # file_ext
	23, # score
)



# --------------
#  File formats
# --------------

# Required to map file extensions to the type of file, such as videos, images, etc.
MD_VIDEO = (
	'mp4',
	'webm',
	'3gp',
	'mpeg',
	'ogg',
	'avi',
)

# Legends never die
# If you're reading this - please do a minute of silence
# in memory of Adobe Flash PLayer.

# Pro tip: it's possible to download Flash player
# as a standalone application from https://airsdk.harman.com/runtime
MD_FLASH = (
	'swf',
)

MD_IMG = (
	'png',
	'jpeg',
	'jpg',
	'webp',
	'avif',
	'bmp',
	'tiff',
	'jfif',
)

# todo: Webp is sexy, but FUCK, webp can be both an image and animation...
MD_IMG_ANIMATED = (
	'gif',
	'apng',
	# 'webp',
)



# ============================
#             Util
# ============================

# Split a list into a specified amount of equal parts
def split_list(lst, n):
	"""
		lst = target list.
		n = size of a single chunk.
	"""
	return [lst[i:i + n] for i in range(0, len(lst), n)]

# fuck python
# fuck it very much. Retard
def print_exception(err):
	import traceback
	try:
		print(
			''.join(
				traceback.format_exception(
					type(err),
					err,
					err.__traceback__
				)
			)
		)
	except Exception as e:
		print(e)

# Freeze into limbo state.
# If script reaches end - everything tries to terminate itself,
# breaks and spams exceptions
def freeze():
	while True:
		time.sleep(0.1)

def sep():
	print()
	print()

class PerfTest:
	"""
		A very simple performance evaluator.
		Measures the amount of time spent executing code
		in the context.
	"""
	def __init__(
		self,
		msg =       'Perftest: ',
		ms =        True,
		as_return = False,
		log_lvl =   1,
		cpu_t =     False
	):
		"""
		msg     = text message to print/return
		ms      = return time in milliseconds instead of seconds
		log_lvl = log level required for the message to print
		cpu_t   = use time.process_time() instead of time.time()
		"""
		self.time = time
		self.use_cpu_time = cpu_t
		self.start = time.process_time_ns() if cpu_t else time.time()
		self.as_ms = ms
		self.msg = msg
		self.as_return = as_return
		self.final = ''

		self.need_log_level = log_lvl
		self.env_log_level = 1

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if not self.use_cpu_time:
			mtime = (self.time.time() - self.start) * (1000 if self.as_ms else 1)
		else:
			mtime = (
				(self.time.process_time_ns() - self.start) /
				1_000_000 /
				(1 if self.as_ms else 1000)
			)
		if self.as_return:
			self.final = f'{self.msg} @@ {mtime}'
		else:
			if self.need_log_level == self.env_log_level and self.env_log_level != 0:
				print(self.msg, mtime)




# ============================
#           The shit
# ============================


def filter_post(filter_cache, post_string):
	post = pipe_struct(post_string)

	if filter_cache.has_filter_OFTYPE:
		if not post['file_ext'] in filter_cache.type_map[filter_cache.filter_OFTYPE]:
			return False

	if filter_cache.has_filter_NO:
		if len(post['tag_string'] & filter_cache.tags_NO) > 0:
			return False

	if filter_cache.has_filter_MANDATORY:
		if len(post['tag_string'] & filter_cache.tags_MANDATORY) != filter_cache.MANDATORY_LEN:
			return False

	if filter_cache.has_filter_ONEOF:
		if len(post['tag_string'] & filter_cache.tags_ONEOF) <= 0:
			return False

	for partial in filter_cache.tgquery['partial']:
		if partial in post['tag_string_original']:
			return False

	return True

def pipe_struct(entry_string):
	data_dict = dict(
		zip(DB_STRUCT, entry_string.split(SEP_CHAR))
	)

	data_dict['tag_string_original'] = data_dict['tag_string']
	data_dict['tag_string'] = set(data_dict['tag_string'].split(' '))
	data_dict['score'] = int(data_dict['score'])

	return data_dict

def create_db_chunk(pool, cmd_pipe, prog_pipe):
	DBChunk(pool, cmd_pipe, prog_pipe).run()




class FilterCache:
	"""
		Stores filter data for swift access.
	"""
	def __init__(self):
		self.update()

	def update(self):
		import tag_match
		importlib.reload(tag_match)
		import tag_match

		self.tgquery = tag_match.tgmatch

		self.has_filter_NO =        len(self.tgquery['no']) > 0
		self.has_filter_MANDATORY = len(self.tgquery['yes']) > 0
		self.MANDATORY_LEN =        len(self.tgquery['yes'])
		self.has_filter_ONEOF =     len(self.tgquery['perhaps']) > 0
		self.has_filter_OFTYPE =    not not self.tgquery['of_type']

		self.tags_NO =        set(self.tgquery['no'])
		self.tags_MANDATORY = set(self.tgquery['yes'])
		self.tags_ONEOF =     set(self.tgquery['perhaps'])
		self.filter_OFTYPE =  self.tgquery['of_type']

		self.type_map = {
			'flash': set(MD_FLASH),
			'video': set(MD_VIDEO),
			'image': set(MD_IMG),
			'animated_image': set(MD_IMG_ANIMATED),
		}


class DBChunk:
	UPDATE_DIV = 20

	def __init__(self, pool, cmd_pipe, prog_pipe):
		self.alive = True
		self.filter_cache = FilterCache()

		# Array containing all the rows
		self.pool = tuple(pool or [])

		# Array containing indices pointing to elements inside .pool array,
		# which passed filtering.
		self.filtered = []

		self.cmd_pipe = cmd_pipe
		self.prog_pipe = prog_pipe

	def terminate(self, _=None):
		self.pool = None
		self.filtered.clear()
		self.filtered = None
		self.alive = False

		self.prog_pipe.send(0.0)

		return True

	def run(self):
		try:
			while self.alive:
				cmd, cmd_data = self.cmd_pipe.recv()
				# print('Worker received command:', cmd)
				self.cmd_pipe.send(
					getattr(self, cmd)(cmd_data)
				)

				cmd = None
				cmd_data = None
		except Exception as e:
			print_exception(e)

		print('Stopping chunk...')

	def run_filter(self, *args):
		update_rate = math.ceil(len(self.pool) / self.UPDATE_DIV)
		prog = 0

		self.filter_cache.update()
		self.filtered.clear()

		for i, post in enumerate(self.pool):
			if filter_post(self.filter_cache, post):
				self.filtered.append(i)
			if i % update_rate == 0:
				self.prog_pipe.send(prog / self.UPDATE_DIV)
				self.prog_pipe.recv()
				prog += 1

		self.prog_pipe.send(1.0)
		self.prog_pipe.recv()

		return len(self.filtered)

	def get_post_info(self, post_idx):
		return pipe_struct(
			self.pool[self.filtered[post_idx]]
		)

	def create_sorted_index(self, criteria):
		sorting_index = []
		for i, post in enumerate(self.filtered):
			post = self.pool[post]

			sorting_index.append((
				i,
				criteria(post)
			))

		self.prog_pipe.send(1.0)
		self.prog_pipe.recv()

		return sorting_index

	def get_filtered_save_data(self, _):
		return self.filtered

	def get_pool_size(self, _):
		return len(self.pool)

	def apply_filtered_index(self, saved_index):
		self.filtered.clear()
		self.filtered.extend(saved_index)


class DBChunkWorker:
	"""
		Controls a single DB chunk.
		This is purely multiprocess.Process stuff.
	"""
	def __init__(self, db_records, prog_callback=None):
		self.alive = True

		# Function triggered once a worker made some progress
		self.prog_callback = prog_callback

		# CMD pipe
		cmd_pipe_a, cmd_pipe_b = multiprocessing.Pipe()
		self.cmd_pipe = cmd_pipe_b

		# Progress report pipe
		prog_pipe_a, prog_pipe_b = multiprocessing.Pipe()
		self.prog_pipe = prog_pipe_b

		# The worker proccess itself
		self.worker_process = multiprocessing.Process(
			target=create_db_chunk,
			args=(db_records, cmd_pipe_a, prog_pipe_a,)
		)
		self.worker_process.start()

		# Progress watcher thread
		self.prog_thread = threading.Thread(
			target=self.prog_report,
		)
		self.prog_thread.start()

		# print('Chunk worker initialized')

	def terminate(self):
		self.alive = False
		self.prog_callback = None

		self.send_cmd('terminate')
		self.read_cmd()

		self.prog_thread.join()
		self.prog_thread = None

		self.worker_process.join()

		return True

	def prog_report(self):
		try:
			while self.alive:
				prog = self.prog_pipe.recv()
				if self.prog_callback:
					self.prog_callback(self, prog)
				self.prog_pipe.send(True)
		except Exception as e:
			print_exception(e)

	def send_cmd(self, func_name, func_data=None):
		self.cmd_pipe.send(
			(func_name, func_data)
		)

	def read_cmd(self):
		return self.cmd_pipe.recv()

	def run_cmd(self, func_name, func_data=None):
		self.send_cmd(func_name, func_data)

		return self.read_cmd()

	def __getattr__(self, func_name):
		return (
			lambda func_data=None: self.run_cmd(func_name, func_data)
		)

	def __get__(self, func_name):
		return (
			lambda func_data=None: self.run_cmd(func_name, func_data)
		)



class ChunkedDB:
	"""
		DB reconstruction consisting of chunks, where each record is a string
		inside a python list.
		Each DB chunk is a multiprocessing.Process.
		The amount of chunks depends on either:
		    - CPU_USAGE_FACTOR (float):
		      The PC's core count is multiplied by this number,
		      rounded down (percentage moment) and the resulting integer
		      determines the amount of DB chunks.
		    - worker_amount (int) __init__ argument:
		      Overwrites CPU_USAGE_FACTOR.
		      Simply creates as many workers as specified in the argument.

		Filtered rows are stored in .filtered_index array of tuples
		containing the following items:
		    0 - Row index relative to the parent worker.
		        Basically, an integer which points to an element inside worker's
		        .filtered array.
		    1 - Worker class reference. Reference to the worker class this index
		        belongs to.

		Each <DBChunkWorker> owns exactly one <DBChunk> child
		and acts as a proxy (proxies moment).

		The logic is as follows:
		    - The database: ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']
		    - Each worker (DBChunk) stores:
		      1. All the DB entries assigned to it inside .pool:
		         ['d', 'e', 'f', 'g']
		      2. An array with indexes (.filtered) pointing to elements inside .pool:
		         [ 0,   2,   3  ], which translates to:
		         ['d', 'f', 'g' ]
		    - The ChunkedDB class has an array of tuples (.filtered_index),
		      containing the following items:
		          0 - an integer which points to an element inside <DBChunk>'s
		              .filtered array.
		          1 - Worker class reference. Reference to a <DBChunkWorker> class
		              this index belongs to. <DBChunkWorker> is literally the same
		              as <DBChunk>, all it does is proxy some shit for technical
		              reasons...
		              From now on - <DBChunkWorker> will be referenced as "<DBChunk>",
		              because they're the same things.

		      A tuple inside <ChunkedDB>.filtered_index:
		      (K, <DBChunk>)
		      Where "K" is any element (integer) from <DBChunk>.filtered_index
		      It's referenced as "K" purely for convenience.

		      <DBChunk>:
		          - .pool:               ['d', 'e', 'f', 'g']
		          - .filtered:           [ 0,        2,   3 ]
		          - Which means:         [ 0,        1,   2 ]
		      <ChunkedDB>:
		          - .filtered_index[N]: [K, <DBChunk>]

		      Which means retreiving a row's data goes as follows:

		      N = Any integer within <ChunkedDB>.filtered_index limits.
		      A = <ChunkedDB>.filtered_index[N]
		      B = A[0] = K
		      C = A[1]

		      C.pool[C.filtered[K]] = 'f'

		All of the hardcore BDSM described above allows for search queries to be
		multiprocessed and be faster by a factor depending on the amount of
		cores the CPU has.

	"""

	# Basically, CPU usage percentage
	# 1.0 = 100% (don't do that)
	# 0.0 caps to 0.1 (don't do that too)
	# 0.8 seems to be the most efficient
	CPU_USAGE_FACTOR = 0.8

	def __init__(
		self,
		db_records,
		worker_amount=None,
		prog_callback=None,
		worker_init_callback=None,
	):
		self.filtered_index = []

		self.worker_amount = worker_amount or math.floor(
			(os.cpu_count() or 6) * max(self.CPU_USAGE_FACTOR, 0.1)
		)

		# An array containing all the worker classes
		# self.chunks = list(map(
		# 	lambda chunk: DBChunkWorker(chunk, prog_callback),
		# 	split_list(
		# 		db_records,
		# 		int(len(db_records) / self.worker_amount)
		# 	)
		# ))

		# The method above was replaced with this one to enable progress reporting
		self.chunks = split_list(
			db_records,
			math.floor(len(db_records) / self.worker_amount)
		)

		for i, chunk_data in enumerate(self.chunks):
			self.chunks[i] = DBChunkWorker(chunk_data, prog_callback)
			if worker_init_callback:
				worker_init_callback(
					(i+1) / len(self.chunks)
				)

		self.quick_sort = QuickSort(self)

	def terminate(self):
		self.filtered_index.clear()
		self.filtered_index = None

		for chunk in self.chunks:
			chunk.terminate()

		print('Terminated all chunks')
		return True

	def run_filter(self):
		self.filtered_index.clear()
		for chunk in self.chunks:
			# print('Sending filter command')
			chunk.send_cmd('run_filter')

		for chunk in self.chunks:
			# print('Filter executed')
			self.filtered_index.extend(map(
				lambda post_widx: (post_widx, chunk),
				range(chunk.read_cmd())
			))

	def get_post_info(self, fidx):
		# fidx = Filtered Index.
		# Points to an element inside ChunkedDB's .filtered_index array.

		# wp_idx = Worker Pool Index.
		# points to an element inside worker's .filtered array

		wp_idx, worker = self.filtered_index[fidx]
		return worker.get_post_info(wp_idx)

	def save_state(self, tgt_fpath=GAMESAVE_FPATH, extras=None):
		tgt_fpath.unlink(missing_ok=True)

		with open(tgt_fpath, 'wb') as tgt_file:
			pickle.dump(
				{
					'data': [c.get_filtered_save_data() for c in self.chunks],
					'db_len': sum(c.get_pool_size() for c in self.chunks),
					'sorted': [
						(i[0], self.chunks.index(i[1]),) for i in self.filtered_index
					],
					'extras': extras
				},
				tgt_file
			)

	def apply_saved_state(self, save_data):
		if len(save_data['data']) != len(self.chunks):
			print("""Couldn't load save data: different worker count. Aborting""")
			return

		if sum(c.get_pool_size() for c in self.chunks) != save_data['db_len']:
			print(
				"""Cooked DB size differs from the one saved """
				"""in the gamesave. Aborting"""
			)
			return

		for idx_data, chunk in zip(save_data['data'], self.chunks):
			chunk.apply_filtered_index(idx_data)
		# for idx, chunk in enumerate(self.chunks):
			# chunk.apply_filtered_index(save_data['data'][idx])

		self.filtered_index.clear()
		for fidx, chunk_idx in save_data['sorted']:
			self.filtered_index.append((
				fidx,
				self.chunks[chunk_idx]
			))


class QuickSortCriterias:
	@staticmethod
	def score_criteria(post_str):
		return int(post_str.split(SEP_CHAR)[23]) * -1

	@staticmethod
	def newest_criteria(post_str):
		return int(post_str.split(SEP_CHAR)[0]) * -1

	@staticmethod
	def oldest_criteria(post_str):
		return int(post_str.split(SEP_CHAR)[0])

	@staticmethod
	def videos_criteria(post_str):
		order = (
			MD_VIDEO,
			MD_IMG_ANIMATED,
			MD_FLASH,
			MD_IMG,
		)

		ext = post_str.split(SEP_CHAR)[11]
		for grp in order:
			if ext in grp:
				return order.index(grp)

		return 0

	@staticmethod
	def images_criteria(post_str):
		order = (
			MD_IMG,
			MD_IMG_ANIMATED,
			MD_FLASH,
			MD_VIDEO,
		)

		ext = post_str.split(SEP_CHAR)[11]
		for grp in order:
			if ext in grp:
				return order.index(grp)

		return 0

	@staticmethod
	def anims_criteria(post_str):
		order = (
			MD_IMG_ANIMATED,
			('webp',),
			MD_VIDEO,
			MD_FLASH,
			MD_IMG,
		)

		ext = post_str.split(SEP_CHAR)[11]
		for grp in order:
			if ext in grp:
				return order.index(grp)

		return 0


	# Rating
	@staticmethod
	def rating_s_criteria(post_str):
		order = ('s', 'q', 'e')
		return order.index(post_str.split(SEP_CHAR)[5])

	@staticmethod
	def rating_q_criteria(post_str):
		order = ('q', 'e', 's')
		return order.index(post_str.split(SEP_CHAR)[5])

	@staticmethod
	def rating_e_criteria(post_str):
		order = ('e', 'q', 's')
		return order.index(post_str.split(SEP_CHAR)[5])


class QuickSort:
	"""
		Takes ChunkedDB class as an input.
		QuickSort is needed to quickly sort the filtered records by
		score, rating and so on.

		The way it works is genius:
		(sometimes, my genius... it's almost frightening)
		    - First, records are sorted locally inside chunks.
		    - The sorted index is then collected by the main process.
		    - The collected stuff is then used to sort the main index.
	"""
	def __init__(self, chunked_db):
		self.chunked_db = chunked_db
		self.chunks = chunked_db.chunks
		self.filtered_index = chunked_db.filtered_index

	def run(self, criteria=None):
		sorted_index = {}
		for chunk in self.chunks:
			sorted_index[chunk] = {
				k: v for k, v in chunk.create_sorted_index(criteria)
			}
			print('Created sorted index for', chunk)


		self.filtered_index.sort(
			key=lambda p: sorted_index[p[1]][p[0]]
		)



class FileWrapper:
	"""
		A wrapper for file objects to track the amount of data read.
	"""
	def __init__(
		self,
		file,
		total=0,
		callback=None,
		is_text=False,
		update_rate=1024**2
	):
		self._file = file
		self._bytes_read = 0

		self.total = total
		self.callback = callback
		self.is_text = is_text
		self.update_rate = update_rate
		self.next_update = update_rate

	def trigger_callback(self):
		if self.callback and (self.bytes_read >= self.next_update):
			self.callback(self._bytes_read / self.total)
			self.next_update += self.update_rate

	@staticmethod
	def callback_wrap(method):
		def wrap(self, *args, **kwargs):
			result = method(self, *args, **kwargs)
			self.trigger_callback()
			return result

		return wrap

	@property
	def bytes_read(self):
		"""Returns the total number of bytes read."""
		return self._bytes_read

	@callback_wrap
	def read(self, size=-1):
		"""Reads data from the file and updates the bytes read counter."""
		data = self._file.read(size)
		self._bytes_read += len(data)

		if self.is_text:
			return data.decode('utf-8')
		else:
			return data

	@callback_wrap
	def readline(self, size=-1):
		"""Reads a single line from the file and updates the bytes read counter."""
		line = self._file.readline(size)
		self._bytes_read += len(line)

		if self.is_text:
			return line.decode('utf-8')
		else:
			line

	@callback_wrap
	def readlines(self, hint=-1):
		"""Reads all lines from the file and updates the bytes read counter."""
		lines = self._file.readlines(hint)
		self._bytes_read += sum(len(line) for line in lines)
		return lines

	def close(self):
		self._file.close()

	def __getattr__(self, attr):
		"""Delegates attribute access to the underlying file object."""
		return getattr(self._file, attr)

	def __iter__(self):
		"""Allows iteration over the file wrapper."""
		for line in self._file:
			self._bytes_read += len(line)
			self.trigger_callback()
			if self.is_text:
				yield line.decode(encoding='utf-8')
			else:
				yield line

	def __enter__(self):
		"""Supports context management."""
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self._file.close()


class GZCooker:
	"""
		Standartized gz util.
		Made specifically to deal with https://fuck/filename.extension.gz and
		nothing else.
	"""
	DL_CHUNK_SIZE = (1024**2)*32

	def __init__(
		self,
		src_url,
		cache_filepath=None,
		callback=None,
		read_mode='rb+',
		chunk_size=DL_CHUNK_SIZE,
		is_text=True
	):
		self.base_headers = {
			'user-agent': (
				'E621 Extended Query '
				'"https://github.com/MrKleiner/e621_extq"'
			),
		}

		self.src_url = src_url
		self.cache_filepath = Path(cache_filepath) if cache_filepath else None
		self.callback = callback

		self.read_mode = read_mode

		# Python gzip objects, NOT just a simple file
		self._fbuf_cached = None
		self._fbuf_stream = None

		self.chunk_size = chunk_size
		self.is_text = is_text

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		if self._fbuf_cached:
			self._fbuf_cached.close()

		if self._fbuf_stream:
			self._fbuf_stream.close()

		self._fbuf_cached = None
		self._fbuf_stream = None

	@property
	def fbuf_cached(self):
		if self._fbuf_cached:
			return self._fbuf_cached

		dl_request = requests.get(
			url=self.src_url,
			headers=self.base_headers,
			stream=True
		)

		dl_size = int(dl_request.headers.get('content-length') or 1)

		with open(self.cache_filepath, 'wb') as out_file:
			with gzip.GzipFile(fileobj=dl_request.raw, mode='rb') as decompressed_file:
				for chunk in iter(lambda: decompressed_file.read(self.chunk_size), b''):
					out_file.write(chunk)
					if self.callback:
						self.callback(dl_request.raw.tell() / dl_size)

		self._fbuf_cached = open(
			self.cache_filepath,
			self.read_mode,
			encoding='utf-8'
		)
		return self._fbuf_cached

	@property
	def fbuf_stream(self):
		dl_request = requests.get(
			url=self.src_url,
			headers=self.base_headers,
			stream=True
		)

		dl_size = int(dl_request.headers.get('content-length') or 1)

		self._fbuf_stream = FileWrapper(
			gzip.GzipFile(
				fileobj=FileWrapper(
					dl_request.raw,
					total=dl_size,
					callback=self.callback,
					update_rate=self.chunk_size
				),
				mode='rb'
			),
			is_text=self.is_text
		)

		return self._fbuf_stream


class DLURLExtractor:
	def __init__(self, html, base_name):
		self.html = html

		self._date_based = None
		self._size_based = None

		self.base_name = base_name

	@property
	def size_based(self):
		if self._size_based:
			return self._size_based

		# Store the child list, since generators are useless here
		child_list = list(
			self.html.select('body > pre')[0].children
		)

		"""
			There are different db exports.
			For now, aim for the most complete one,
			which is also the largest.

			Unfortunately, the HTML page containing the links
			is very retarded: "a" DOM elements are completely
			separated from their description, basically:
			<a></a> "date size"
			<a></a> "date size"

			Fortunately, the required file is also the largest:
			- Iterate over all the entries in the list of links
			- Find the largest number
			- Write down the index of the DOM node, that has the said number
			- Iterate over the child list backwards, starting from the index
			  mentioned above
			- Stop iteration on first <a> tag and get its href
		"""

		# todo: store a tuple of size + child index
		# and then simply filter it or something,
		# instead of iterating over the HTML tree over
		# and over again

		# Find the largest number (file size)

		target_size = 0

		for node in child_list:
			# print('Looking up node:', node)
			node_contents = str(node).strip()
			if node.name != 'a' and node_contents:
				# print('Evaluating node text:', node)
				size = int(
					node_contents.split(' ')[-1]
				)
				if size > target_size:
					target_size = size

		# Well, yes
		target_size = str(target_size)


		# Find the index of the node, that has the target number
		target_child_idx = 1
		for idx, node in enumerate(child_list):
			if node.name != 'a' and str(node).strip():
				if target_size in str(node):
					target_child_idx = idx
					break

		# Iterate over the target node list
		# backwards, starting from the target index
		target_link = None
		for idx in range(len(child_list)):
			node = child_list[target_child_idx - idx]
			if node.name == 'a':
				target_link = node['href'].strip()
				# print('found sex:', str(node))
				break

		self._size_based = target_link
		return self._size_based

	@property
	def date_based(self):
		if self._date_based:
			return self._date_based

		child_list = list(
			self.html.select('body > pre a')
		)

		latest = None

		for node in child_list:
			# if not (self.base_name in node['href']) or not node['href']:
			if not (node['href'] or '').startswith(self.base_name) or not node['href']:
				continue

			date = datetime.strptime(
				'-'.join(node['href'].split('-')[1:]).split('.')[0],
				'%Y-%m-%d'
			)

			if (not latest) or (date > latest[0]):
				latest = (date, node,)

		self._date_based = latest[1]['href']
		return self._date_based


class DBCooker:
	"""
		DB Cooker.
		Downloads and cooks the database.
		Cooking the db involves:
			- Downloading the DB gzip.
			- Unpacking the gzip from above.
			- Reading and evaluating the mentioned gzip.
		    - Filtering out deleted posts and posts with negative rating,
		      as they're useless.
		    - Deleting most columns to save on RAM.
		      This system only requires a couple columns to work.
		      Misc. info about the post can be viewed on e621 website itself.

		The cooked DB array is cleared with ".clear()" on __exit__ to save RAM.
	"""

	CSV_FIELD_SIZE_LIMIT = (1024**2)*16

	TEST_MODE = False
	TEST_MODE_DL_URL = 'http://127.0.0.1:8000/posts-2024-12-10.csv.gz'

	def __init__(
		self,
		force_redownload=False,
		keep_cache=False,
		preserve_details=False,
		callbacks=None,
		cached=True
	):
		# Base headers used to make HTTP requests to e621.
		self.base_headers = {
			'user-agent': (
				'E621 Extended Query '
				'"https://github.com/MrKleiner/e621_extq"'
			),
		}

		# Callback functions for reporting, in order:
		# 1 - gzip DB file download progress
		# 2 - cooking progress
		# Exactly one argument is passed:
		# float 0.0 - 1.0 indicating the progress percentage.
		self.callbacks = {
			'dl': None,
			'cook': None,
		} | (callbacks or {})

		# Gzip download URL.
		# Retreiving it is a whole process...
		self._download_url = None

		# Gzip file open in rb+ mode, containing DB csv file.
		# Doesn't exist when cached=True
		self._packed_db = None

		# Gzip python object, derived from the downloaded gzip DB file.
		# Used to eval the csv file as it's being unpacked to save resources.
		# Doesn't exist when cached=True
		self._gz_unpacker_buf = None

		# An array representing the DB rows, with all non-crucial "columns"
		# replaced with an empty string ('').
		# Each array entry is actually a single string to save on RAM.
		# Column separator is a null char (SEP_CHAR).
		self._cooked_db = None

		# Whether to first download the gz file to disk and only then unpack it.
		# Otherwise:
		# - Downloaded gz bytes are fed directly into gz unpacker.
		# - Unpacked bytes from above are fed directly into cooker.
		self.cached = cached
		# Whether to automatically delete the downloaded gzip file (when applicable).
		# Triggered on __exit__
		self.keep_cache = keep_cache
		# Whether to force-redownload the gzip file even if it exists.
		self.force_redownload = force_redownload
		# Whether to delete non-crucial DB columns.
		self.preserve_details = preserve_details

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		close_targets = (
			self._packed_db,
			self._gz_unpacker_buf,
		)

		for close_target in close_targets:
			try:
				close_target.close()
			except: pass

		self._packed_db = None
		self._gz_unpacker_buf = None

		if not self.keep_cache:
			DB_GZIP_CACHE_FPATH.unlink(missing_ok=True)

		if self._cooked_db != None:
			self._cooked_db.clear()
			self._cooked_db = None

		return

	@property
	def _OLD_download_url(self):
		if self._download_url:
			return self._download_url

		# Get the HTML page containing target file names
		ftp_html = jquery(
			requests.get(url=DB_DL_BASE_URL, headers=self.base_headers).content,
			'html.parser'
		)

		# Store the child list, since generators are useless here
		child_list = list(
			ftp_html.select('body > pre')[0].children
		)

		"""
			There are different db exports.
			For now, aim for the most complete one,
			which is also the largest.

			Unfortunately, the HTML page containing the links
			is very retarded: "a" DOM elements are completely
			separated from their description, basically:
			<a></a> "date size"
			<a></a> "date size"

			Fortunately, the required file is also the largest:
			- Iterate over all the entries in the list of links
			- Find the largest number
			- Write down the index of the DOM node, that has the said number
			- Iterate over the child list backwards, starting from the index
			  mentioned above
			- Stop iteration on first <a> tag and get its href
		"""

		# todo: store a tuple of size + child index
		# and then simply filter it or something,
		# instead of iterating over the HTML tree over
		# and over again

		# Find the largest number (file size)

		target_size = 0

		for node in child_list:
			# print('Looking up node:', node)
			node_contents = str(node).strip()
			if node.name != 'a' and node_contents:
				# print('Evaluating node text:', node)
				size = int(
					node_contents.split(' ')[-1]
				)
				if size > target_size:
					target_size = size

		# Well, yes
		target_size = str(target_size)


		# Find the index of the node, that has the target number
		target_child_idx = 1
		for idx, node in enumerate(child_list):
			if node.name != 'a' and str(node).strip():
				if target_size in str(node):
					target_child_idx = idx
					break

		# Iterate over the target node list
		# backwards, starting from the target index
		target_link = None
		for idx in range(len(child_list)):
			node = child_list[target_child_idx - idx]
			if node.name == 'a':
				target_link = node['href'].strip()
				# print('found sex:', str(node))
				break

		self._download_url = target_link
		return self._download_url

	@property
	def download_url(self):
		if self._download_url:
			return self._download_url

		self._download_url = DLURLExtractor(
			jquery(
				requests.get(url=DB_DL_BASE_URL, headers=self.base_headers).content,
				'html.parser'
			),
			'posts-'
		)

		return self._download_url

	@property
	def packed_db(self):
		if self._packed_db:
			return self._packed_db

		if not self.force_redownload and DB_GZIP_CACHE_FPATH.is_file():
			self._packed_db = open(DB_GZIP_CACHE_FPATH, 'rb+')
			return self._packed_db

		DB_GZIP_CACHE_FPATH.unlink(missing_ok=True)

		# Send the request to the download,
		# but only read headers from the response
		# and download the database later, as a stream.

		# This operation is split into a number of steps
		# purely for proper callbacks stuff
		dl_request = requests.get(
			url=DB_DL_BASE_URL + self.download_url,
			headers=self.base_headers,
			stream=True
		)

		# todo: as of 01-02-2024 the database size grows exponentially
		# how long till the server stops providing the content-length header?
		dl_size = int(dl_request.headers.get('content-length') or 1)

		dl_progress = 0
		with open(DB_GZIP_CACHE_FPATH, 'ab') as tgt_file:
			# todo: is this chunksize fine ?
			# for chunk in dl_request.iter_content(chunk_size=8192*2):
			for chunk in dl_request.iter_content(chunk_size=1024*2):
				tgt_file.write(chunk)
				dl_progress += len(chunk)

				# todo: Does this even make sense?
				# Why not just specify a large chunk size?
				if dl_progress % ((1024**2)*16) == 0:
					# print('Downloading DB:', dl_progress / dl_size)
					if self.callbacks['dl']:
						self.callbacks['dl'](dl_progress / dl_size)

		self._packed_db = open(DB_GZIP_CACHE_FPATH, 'rb+')
		return self._packed_db

	@property
	def gz_unpacker_buf(self):
		if self._gz_unpacker_buf:
			return self._gz_unpacker_buf

		self._gz_unpacker_buf = gzip.open(
			self.packed_db,
			mode='rt',
			encoding='utf-8'
		)

		return self._gz_unpacker_buf

	@property
	def cooked_db(self):
		if self._cooked_db:
			return self._cooked_db

		self._cooked_db = []

		if self.TEST_MODE:
			dl_url = self.TEST_MODE_DL_URL
		else:
			dl_url = DB_DL_BASE_URL + self.download_url.date_based

		# dl_url = self.TEST_MODE_DL_URL if self.TEST_MODE else (DB_DL_BASE_URL + self.download_url)

		with GZCooker(dl_url, DB_GZIP_CACHE_FPATH, self.callbacks['cook']) as gz_cooker:
			# Some posts have description the size of a fucking novel, while
			# python's csv module has row size limit, which is always active
			# and is by default set to a number too low to account for the
			# novels mentioned above.
			csv.field_size_limit(self.CSV_FIELD_SIZE_LIMIT)

			# The dialect='excel' is for whatever reason the only syntax scheme
			# capable of reading the target csv files
			reader = csv.reader(gz_cooker.fbuf_stream, dialect='excel')

			# First line is column names. Not needed
			next(reader)

			for db_entry in reader:
				# Deleted and negatively rated posts are always skipped,
				# because they're absolutely useless. Especially deleted ones...
				if (db_entry[20] != 't') and not (db_entry[23].startswith('-')):
					# Delete non-crucial fields
					if not self.preserve_details:
						for i, _ in enumerate(db_entry):
							if not i in DB_STRUCT_PASS:
								db_entry[i] = ''
					self._cooked_db.append(SEP_CHAR.join(db_entry))

		return self._cooked_db


class TagCooker:
	"""
		Same as DBCooker, but for tags
	"""

	TEST_MODE = False
	TEST_MODE_DL_URL = 'http://127.0.0.1:8000/tags-2024-12-10.csv.gz'

	def __init__(
		self,
		preserve_empty=False,
		callback=None
	):
		self.base_headers = {
			'user-agent': (
				'E621 Extended Query '
				'"https://github.com/MrKleiner/e621_extq"'
			),
		}

		self.preserve_empty = preserve_empty
		self.callback = callback

		self._cooked_tags = None
		self._dl_url = None

		self._tags = None

	@property
	def dl_url(self):
		if self._dl_url:
			return self._dl_url

		self._dl_url = DLURLExtractor(
			jquery(
				requests.get(url=DB_DL_BASE_URL, headers=self.base_headers).content,
				'html.parser'
			),
			'tags-'
		)

		return self._dl_url

	@property
	def cooked_tags(self):
		if self._cooked_tags:
			return self._cooked_tags

		if self.TEST_MODE:
			dl_url = self.TEST_MODE_DL_URL
		else:
			dl_url = DB_DL_BASE_URL + self.dl_url.date_based

		with GZCooker(dl_url, callback=self.callback, chunk_size=1024*8) as gz_cooker:
			reader = csv.reader(gz_cooker.fbuf_stream, dialect='excel')

			# First line is column names. Not needed
			next(reader)

			self._cooked_tags = []

			for tag in reader:
				if int(tag[3]) <= 0:
					continue
				self._cooked_tags.append(tag[1])

		return self._cooked_tags







# ============================
#           Testing
# ============================

def print_first_page(db, count=80):
	print(
		'id'.ljust(10),
		'md5'.ljust(40),
		'score'.ljust(40),
		'file_ext'.ljust(15),
		'rating'.ljust(15),
	)
	print()
	for i in range(count):
		row_data = db.get_post_info(i)
		print(
			row_data['id'].ljust(10),
			row_data['md5'].ljust(40),
			str(row_data['score']).ljust(40),
			str(row_data['file_ext']).ljust(15),
			str(row_data['rating']).ljust(15),
		)

def test_callback(worker, prog):
	print('Filter progress report:', worker, prog)

def test_worker_init_callback(prog):
	print('Worker init:', prog)

def test():
	cbacks = {
		'dl':   test_db_cooker_dl_callback,
		'cook': test_db_cooker_cook_callback,
	}

	if not COOKED_DB_FPATH.is_file():
		with DBCooker(True, False, callbacks=cbacks) as db_cooker:
			with open(COOKED_DB_FPATH, 'wb') as tgt_file:
				pickle.dump(
					db_cooker.cooked_db,
					tgt_file,
					protocol=pickle.HIGHEST_PROTOCOL
				)

	with PerfTest('Loading Cooked DB:'):
		with open(COOKED_DB_FPATH, 'rb') as tgt_file:
			chunked_db = ChunkedDB(
				pickle.load(tgt_file),
				prog_callback=test_callback,
				worker_init_callback=test_worker_init_callback
			)

	sep()

	with PerfTest('Filtering:'):
		chunked_db.run_filter()

	sep()

	print(
		'id'.ljust(10),
		'md5'.ljust(40),
		'score'.ljust(40),
	)
	print()
	with PerfTest('Getting post info:'):
		print_first_page(chunked_db)

	sep()

	with PerfTest('QuickSort:'):
		chunked_db.quick_sort.run(QuickSortCriterias.score_criteria)

	sep()

	with PerfTest('Getting post info after QuickSort:'):
		print_first_page(chunked_db)

	sep()

	with PerfTest('Saving game:'):
		chunked_db.save_state()

	sep()

	with PerfTest('Shuffling:'):
		secrets.SystemRandom().shuffle(
			chunked_db.filtered_index
		)

	sep()

	with PerfTest('Getting post info after Shuffle:'):
		print_first_page(chunked_db)

	sep()

	with PerfTest('Loading gamesave:'):
		with open(GAMESAVE_FPATH, 'rb') as tgt_file:
			chunked_db.apply_saved_state(
				pickle.load(tgt_file)
			)

	sep()

	with PerfTest('Getting post info after gamesave load:'):
		print_first_page(chunked_db)

	sep()

	print('==== RND LOAD ====')

	sep()

	print('======== STATE A (SAVED) ========')
	secrets.SystemRandom().shuffle(
		chunked_db.filtered_index
	)
	print_first_page(chunked_db)
	chunked_db.save_state()

	sep()

	print('======== STATE B ========')
	secrets.SystemRandom().shuffle(
		chunked_db.filtered_index
	)
	print_first_page(chunked_db)

	sep()

	print('======== LOAD STATE A ========')
	with open(GAMESAVE_FPATH, 'rb') as tgt_file:
		chunked_db.apply_saved_state(
			pickle.load(tgt_file)
		)
	print_first_page(chunked_db)


	sep()

	# 5236226
	print('======== ADDITIVE SORTING ========')
	# chunked_db.quick_sort.run(QuickSortCriterias.oldest_criteria)
	# print_first_page(chunked_db)

	# return

	# additive: aefb48a40aa19f2931d02dcab4165ac7 @ 4636
	# non additive: 4cde67250fc2713af371fb5e497224c2 @ 4829
	# chunked_db.quick_sort.run(QuickSortCriterias.newest_criteria)

	chunked_db.quick_sort.run(QuickSortCriterias.score_criteria)
	chunked_db.quick_sort.run(QuickSortCriterias.videos_criteria)

	sep()

	# print_first_page(chunked_db)

	sep()

	# return

	# QuickSort order n shit
	chunked_db.quick_sort.run(QuickSortCriterias.newest_criteria)
	chunked_db.quick_sort.run(QuickSortCriterias.images_criteria)

	print_first_page(chunked_db, len(chunked_db.filtered_index))

	return

	sep()

	print_first_page(chunked_db)

	sep()

	print('Terminating...')

	sep()

	chunked_db.terminate()

	print('Done Terminating everything...')

	sep()


def test_gz_cooker_callback(prog):
	print('GZ prog:', prog)

def test_gz_cooker():
	src_url = 'https://e621.net/db_export/tags-2024-12-10.csv.gz'
	tgt_file = CACHE_DIR / 'gzcook_test.csv'
	tgt_file.unlink(missing_ok=True)
	with GZCooker(src_url, tgt_file, test_gz_cooker_callback) as csv_file:
		print(len(
			csv_file.fbuf.read().split(b'\n')
		))


def test_db_cooker_dl_callback(prog):
	print('DB Dl progress:', prog)

def test_db_cooker_cook_callback(prog):
	print('DB cook progress:', prog)

def test_db_cooker():
	cbacks = {
		'dl':   test_db_cooker_dl_callback,
		'cook': test_db_cooker_cook_callback,
	}
	with DBCooker(True, False, callbacks=cbacks) as db_cooker:
		with open(COOKED_DB_FPATH, 'wb') as tgt_file:
			pickle.dump(
				db_cooker.cooked_db,
				tgt_file,
				protocol=pickle.HIGHEST_PROTOCOL
			)


def test_tags_callback(prog):
	print('Tag cooking:', prog)

def test_tags():
	tag_cooker = TagCooker(callback=test_tags_callback)

	with open(COOKED_TAGS_FPATH, 'wb') as tgt_file:
		pickle.dump(
			tag_cooker.cooked_tags,
			tgt_file,
			protocol=pickle.HIGHEST_PROTOCOL
		)

	for tag in tag_cooker.cooked_tags:
		print(tag)

	sep()

	print(len(tag_cooker.cooked_tags))


if __name__ == '__main__':
	test()


	sep()
	print(' @@@@@@@@@ END @@@@@@@@@')
	freeze()