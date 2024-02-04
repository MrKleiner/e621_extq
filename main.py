import multiprocessing
from multiprocessing import freeze_support
import threading, socket, json, time, requests, gzip, shutil, struct, csv, importlib, pickle, math, sys
from min_http import MinHTTP
from min_wss import MinWSession
from pathlib import Path
from bs4 import BeautifulSoup as jquery

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


# print('fpath', __file__)


# Some constants
INTERNAL_RES_PATH = None
IS_EXE = 'is_exe' == '@@NOT_EXE'


def devprint(*args, **kwargs):
	if not IS_EXE:
		print(*args, **kwargs)


if IS_EXE:
	# In this case THISDIR refers to the exe location
	THISDIR = Path(sys.executable).parent

	# Two lines below are needed for tag_match importing to work
	INTERNAL_RES_PATH = Path(__file__).parent
	sys.path.append(str(THISDIR))
else:
	THISDIR = Path(__file__).parent

# print('Sys paths', sys.path)

CACHE_DIR = THISDIR / 'data'

# Items that were picked from last query execution
QCACHE_PATH = CACHE_DIR / 'query_data.lzrd'

# Path pointing to the full database
DB_PATH = CACHE_DIR / 'full_db_data.csv'

# Path pointing to the full database, but compressed
DB_PATH_COMPRESSED_SRC = CACHE_DIR / 'full_db_data_compressed.csv.gz'

# Base URL where database exports are
DB_DL_BASE_URL = 'https://e621.net/db_export/'

# images per page
ITEMS_PER_PAGE = 80

# CSV module can do this automatically,
# but then it'd take 20+ gb of RAM
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



# 
# File formats
# 
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
MD_FLASH = (
	'swf',
)

MD_IMG = (
	'jpeg',
	'jpg',
	'png',
	'webp',
	'gif',
	'apng',
	'avif',
	'bmp',
	'tiff',
)

# todo: Webp is sexy, but FUCK, webp can be both an image and animation...
MD_IMG_ANIMATED = (
	'gif',
	'apng',
	# 'webp',
)






# Saving session state
class EXTQSession:
	def __init__(self):
		CACHE_DIR.mkdir(exist_ok=True)

		self.db_cache = []
		self.query_cache = []
		self.user_prefs = {}

	def save_query_cache(self):
		QCACHE_PATH.unlink(missing_ok=True)
		with open(QCACHE_PATH, 'wb') as tgt_file:
			pickle.dump(self.query_cache, tgt_file)

	def load_query_cache(self):
		try:
			with open(QCACHE_PATH, 'rb') as tgt_file:
				self.query_cache = pickle.load(tgt_file)
		except Exception as e:
			print('No cache to read from')
			if not IS_EXE:
				print_exception(e)
			self.query_cache = []

	@property
	def page_count(self):
		if not self.query_cache:
			return 0

		# todo: is len() a property or does it perform potentially expensive calculations?
		return math.floor(
			(len(q_session.query_cache) - 1) / ITEMS_PER_PAGE
		)


# Still very stupid, but much better than immediately
# loading potentially very large amounts of data
# into RAM
q_session = EXTQSession()




# 
# Downloading and extracting the csv database
# 
class DatabaseDownloader:
	wss_cmd = 'dl_db_export_btn'

	def __init__(self, wsession):
		self.wsession = wsession
		q_session.db_cache.clear()
		self.base_headers = {
			'user-agent': 'BigLizard/2.73 (pierogi_z_miesem) email/izoframukaltin@yahoo.com',
		}

	def execute(self, *args):
		tgt_link_fname = self.find_download_url()

		self.download_database(tgt_link_fname)

		self.unpack_db()


	def find_download_url(self) -> str:

		# Get the HTML page containing target file names
		ftp_html = jquery(
			requests.get(url=DB_DL_BASE_URL, headers=self.base_headers).content,
			'html.parser'
		)

		# Store the child list, since generators are useless here
		child_list = list(
			ftp_html.select('body > pre')[0].children
		)

		# There are different db exports.
		# For now, aim for the most complete one,
		# which is also the largest.

		# Unfortunately, the HTML page containing the links
		# is very retarded: "a" DOM eelements are completely
		# separated from their description, basically:
		# <a></a> "date size"
		# <a></a> "date size"

		# Fortunately, the required file is also the largest:
		# - Iterate over all the entries in the list of links
		# - Find the largest number
		# - Write down the index of the DOM node, that has the said number
		# - Iterate over the child list backwards, starting from the index mentioned above
		# - Stop iteration on first <a> tag and get its href

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

		# bollocks
		if not target_link:
			self.wsession.send_json({
				'cmd': 'upd_prog_text',
				'val': 'Could not find the db export link, please report this as a bug',
			})

		return target_link


	def download_database(self, tgt_link):
		DB_PATH_COMPRESSED_SRC.unlink(missing_ok=True)

		# Send the request to the download,
		# but only read headers from the response
		# and download the database later, as a stream.

		# This operation is split into a number of steps
		# purely for proper GUI feedback
		dl_request = requests.get(
			url=DB_DL_BASE_URL + tgt_link,
			headers=self.base_headers,
			stream=True
		)

		# todo: as of 01-02-2024 the database size grows exponentially
		# how long till the server stops providing the content-length header?
		dl_size = int(dl_request.headers.get('content-length') or 1)

		dl_progress = 0
		with open(DB_PATH_COMPRESSED_SRC, 'ab') as tgt_file:
			self.wsession.send_json({
				'cmd': 'upd_prog_text',
				'val': 'Downloading the database',
			})

			# todo: is this chunksize fine ?
			for chunk in dl_request.iter_content(chunk_size=8192*2):
				tgt_file.write(chunk)
				dl_progress += len(chunk)

				# todo: Does this even make sense?
				# Why not just specify a large chunk size?
				if dl_progress % ((1024**2)*16) == 0:
					self.wsession.send_json({
						'cmd': 'update_progress',
						'val': dl_progress / dl_size,
					})


	def unpack_db(self, del_when_done=True):
		DB_PATH.unlink(missing_ok=True)

		# fuck gzip.
		# todo: finally find a way to determine the real
		# size of a gzip file.
		# 7-zip does with ease...
		db_real_size = (1024**3)*4

		processed_amount = 0

		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': 'Unpacking the database'
		})

		with gzip.open(DB_PATH_COMPRESSED_SRC, 'rb') as f_in:
			with open(DB_PATH, 'wb') as f_out:
				# todo: presumably, this is much more efficient
				# shutil.copyfileobj(f_in, f_out)
				while True:
					chunk = f_in.read(1024**2)
					if not chunk:
						break
					f_out.write(chunk)
					processed_amount += len(chunk)

					# todo: is this really needed?
					# why not simply read in huge chunks?
					if processed_amount % (1024**2)*32 == 0:
						self.wsession.send_json({
							'cmd': 'update_progress',
							'val': processed_amount / db_real_size,
						})

		if del_when_done:
			DB_PATH_COMPRESSED_SRC.unlink(missing_ok=True)

		self.wsession.send_json({
			'cmd': 'update_progress',
			'val': 1.0,
		})
		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': 'Done unpacking. You can execute queries now'
		})





# 
# The query itself
# 
class ExtendedQuery:
	wss_cmd = 'exec_query'

	def __init__(self, wsession):
		self.wsession = wsession

		# todo: lmfao
		import tag_match
		importlib.reload(tag_match)
		import tag_match

		self.tgquery = tag_match.tgmatch

		self.report_th = 50_000

	def execute(self, *args):
		if not DB_PATH.is_file():
			self.wsession.send_json({
				'cmd': 'upd_prog_text',
				'val': 'Please download the database first',
			})
			return

		if not q_session.db_cache:
			self.preload_db()

		self.exec_query()

		q_session.save_query_cache()


	def _preload_db(self, preserve_details=False):
		"""
		preserve_details = don't delete "source" and "description"
		"""
		q_session.db_cache.clear()

		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': 'Indexing the database',
		})

		# todo: somehow get the total amount of records
		# problem is, it's impossible to know how many records
		# are there without reading the entire database
		total_records = 4_000_000
		processed_records = 0

		with open(DB_PATH, 'r', encoding='utf-8') as db_data:
			csv.field_size_limit(1024**2)
			reader = csv.DictReader(db_data, dialect='excel')
			# dark_void = next(reader)
			for db_entry in reader:
				if not preserve_details:
					db_entry['source'] = ''
					db_entry['description'] = ''
				
				db_entry['tag_string_original'] = db_entry['tag_string']
				db_entry['tag_string'] = set(db_entry['tag_string'].split(' '))
				db_entry['score'] = int(db_entry['score'])
				q_session.db_cache.append(db_entry)

				processed_records += 1
				if processed_records % 30_000 == 0:
					self.wsession.send_json({
						'cmd': 'update_progress',
						'val': processed_records / total_records,
					})

		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': 'Done Indexing',
		})


	def preload_db(self, preserve_details=False):
		"""
		preserve_details = don't delete "source" and "description"
		"""
		q_session.db_cache.clear()

		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': 'Indexing the database',
		})

		# todo: somehow get the total amount of records.
		# Problem is, it's impossible to know how many records
		# are there without reading the entire database
		total_records = 4_000_000
		processed_records = 0

		with open(DB_PATH, 'r', encoding='utf-8') as db_data:
			csv.field_size_limit(1024**2)
			reader = csv.reader(db_data, dialect='excel')
			fuck = next(reader)
			for db_entry in reader:
				if not preserve_details:
					db_entry[4] = ''
					db_entry[17] = ''

				q_session.db_cache.append(','.join(db_entry))

				processed_records += 1
				if processed_records % 30_000 == 0:
					self.wsession.send_json({
						'cmd': 'update_progress',
						'val': processed_records / total_records,
					})

		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': 'Done Indexing',
		})

	@staticmethod
	def pipe_struct(entry_string, preserve_details=False):
		keys = DB_STRUCT
		values = entry_string.split(',')
		data_dict = dict(zip(keys, values))

		if not preserve_details:
			data_dict['source'] = ''
			data_dict['description'] = ''

		data_dict['tag_string_original'] = data_dict['tag_string']
		data_dict['tag_string'] = set(data_dict['tag_string'].split(' '))
		data_dict['score'] = int(data_dict['score'])

		return data_dict


	def exec_query(self):
		q_session.query_cache.clear()
		if not q_session.db_cache:
			raise BufferError(
				'The database must be precached, before query execution'
			)

		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': 'Executing query',
		})

		db_cache_size = len(q_session.db_cache) - 1

		# todo: use not not
		has_filter_NO =        len(self.tgquery['no']) > 0
		has_filter_MANDATORY = len(self.tgquery['yes']) > 0
		MANDATORY_LEN =        len(self.tgquery['yes'])
		has_filter_ONEOF =     len(self.tgquery['perhaps']) > 0
		has_filter_OFTYPE =    not not self.tgquery['of_type']


		tags_NO =        set(self.tgquery['no'])
		tags_MANDATORY = set(self.tgquery['yes'])
		tags_ONEOF =     set(self.tgquery['perhaps'])
		filter_OFTYPE =  self.tgquery['of_type']


		type_map = {
			'flash': set(MD_FLASH),
			'video': set(MD_VIDEO),
			'image': set(MD_IMG),
			'animated_image': set(MD_IMG_ANIMATED),
		}


		# Because why not,
		# but in reality this should never happen.
		filters_present = (
			has_filter_NO,
			has_filter_MANDATORY,
			MANDATORY_LEN,
			has_filter_ONEOF,
			has_filter_OFTYPE,
			len(self.tgquery['partial']) > 0,
		)

		if not True in filters_present:
			self.wsession.send_json({
				'cmd': 'upd_prog_text',
				'val': 'All filters are empty. Query execution aborted',
			})
			return


		for post_idx, _post in enumerate(q_session.db_cache):
			post = self.pipe_struct(_post)

			if post_idx % self.report_th == 0:
				self.wsession.send_json({
					'cmd': 'update_progress',
					'val': post_idx / db_cache_size,
				})

			partial_fail = False

			# Discard posts with negative rating
			# todo: make this optional
			if post['score'] < 0:
				continue

			# Skip deleted
			if post['is_deleted'] == 't':
				continue

			# Execute base filters
			if has_filter_OFTYPE:
				if not post['file_ext'] in type_map[filter_OFTYPE]:
					continue

			if has_filter_NO:
				if len(post['tag_string'] & tags_NO) > 0:
					continue

			if has_filter_MANDATORY:
				if len(post['tag_string'] & tags_MANDATORY) != MANDATORY_LEN:
					continue

			if has_filter_ONEOF:
				if len(post['tag_string'] & tags_ONEOF) <= 0:
					continue


			# Discard partial matches

			# How this works:
			# A post has 3 tags:
			# chica_(fnaf)  bony_(fnaf)  fasbear_(fnaf)

			# IF any text from below matches like this:
			# chica_(fnaf)  bony_(fnaf)  applejack_(mlp)
			#      ^^^^^^^       ^^^^^^            ^^^^^
			#      _(fnaf)       (fnaf)            (mlp)

			# Then - skip

			# todo: that descirption is a lie, but it doesn't
			# really matter
			for partial in self.tgquery['partial']:
				if partial in post['tag_string_original']:
					partial_fail = True
					break

			if partial_fail:
				continue

			# Finally, save the post to the cache
			q_session.query_cache.append(_post)


		self.wsession.send_json({
			'cmd': 'update_progress',
			'val': 1.0,
		})

		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': 'Done. Results should appear in the area below',
		})
		self.wsession.send_json({
			'cmd': 'upd_hit_count',
			'val': {
				'items': len(q_session.query_cache),
				'pages': q_session.page_count,
			},
		})

		page_lister = PageLister(self.wsession)
		page_lister.list_page(0)






class PageLister:
	wss_cmd = 'list_page'

	def __init__(self, wsession):
		self.wsession = wsession

	def execute(self, page_idx):
		self.list_page(page_idx)

	@staticmethod
	def get_media_type(db_record:list|str):
		# todo: better way of doing this
		# such as static defines
		type_dict = (
			(MD_VIDEO, 'vid'),
			(MD_FLASH, 'flash'),
			# todo: fuck
			(MD_IMG_ANIMATED, 'img_anim'),
			(MD_IMG, 'img'),
		)

		# todo: this smart shit is useless
		# and only slows down the execution
		if type(db_record) == list:
			db_record = db_record
		if type(db_record) == str:
			db_record = db_record.split(',')

		for ext, media_type in type_dict:
			if db_record[11] in ext:
				return media_type


	def list_page(self, PAGE_IDX, from_latest=True):
		if not q_session.query_cache:
			self.wsession.send_json({
				'cmd': 'upd_prog_text',
				'val': 'Warning: Please execute a search query, before browsing pages'
			})
			return

		PAGE_COUNT = q_session.page_count
		PAGE_OFFSET = ITEMS_PER_PAGE * PAGE_IDX
		CACHE_LEN = len(q_session.query_cache) - 1

		if PAGE_IDX > PAGE_COUNT or 0 > PAGE_IDX:
			self.wsession.send_json({
				'cmd': 'upd_prog_text',
				'val': 'Page index out of range'
			})
			return

		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': f'Listing page {PAGE_IDX}'
		})

		media_items = []

		# todo: do these if checks affect the performance too much ?
		if from_latest:
			record_idx = CACHE_LEN - PAGE_OFFSET
		else:
			record_idx = PAGE_OFFSET

		while len(media_items) < ITEMS_PER_PAGE and record_idx <= CACHE_LEN:
			# todo: use [n:n] ?
			# update: nah, quick sort would be harder then
			record = q_session.query_cache[record_idx].split(',')
			rhash = record[3]
			r_ext = record[11]

			# print('Date', record[2])

			media_item_data = {
				'preview': f'https://static1.e621.net/data/preview/{rhash[0:2]}/{rhash[2:4]}/{rhash}.jpg',
				'fullres': f'https://static1.e621.net/data/{rhash[0:2]}/{rhash[2:4]}/{rhash}.{r_ext}',
				'media_type': self.get_media_type(record),
			}

			if from_latest:
				media_items.append(media_item_data)
				record_idx -= 1
			else:
				media_items.insert(0, media_item_data)
				record_idx += 1


		self.wsession.send_json({
			'cmd': 'list_page',
			'val': {
				'for_page': PAGE_IDX,
				'items': media_items,
			},
		})





def wss_session(wsession):
	# Index WSS commands
	wss_cmd_dict = {}
	for cmd_tgt in CMD_REGISTRY:
		wss_cmd_dict[cmd_tgt.wss_cmd] = cmd_tgt

	wsession.send_json({
		'cmd': 'upd_hit_count',
		'val': {
			'items': len(q_session.query_cache),
			'pages': q_session.page_count,
		},
	})

	while True:
		try:
			wss_msg = wsession.recv_message()
			devprint('Client msg', wss_msg)
			try:
				wss_cmd = json.loads(
					wss_msg.decode()
				)
			except Exception as e:
				return

			if wss_cmd.get('cmd') in wss_cmd_dict:
				cmd_class = wss_cmd_dict[wss_cmd['cmd']](wsession)
				cmd_class.execute(wss_cmd.get('val'))


		except Exception as e:
			print_exception(e)
			return



def wss_server(skt):
	skt.listen(2)
	print('WSS Started')
	while True:
		try:
			conn, address = skt.accept()
			wss_session(MinWSession(conn))
		except Exception as e:
			continue



def htserver_process(wss_port):
	from htpage_serv import htserver
	htserver(wss_port)



CMD_REGISTRY = (
	DatabaseDownloader,
	ExtendedQuery,
	PageLister,
)


if __name__ == '__main__':
	freeze_support()

	if IS_EXE:
		if not (THISDIR / 'tag_match.py').is_file():
			shutil.copy(
				INTERNAL_RES_PATH / 'resources' / 'tag_match_sample.py',
				THISDIR / 'tag_match.py',
			)


	q_session.load_query_cache()
	print('Processed query cache')

	# The HTTP server needs to know the socket WSS is running on,
	# before launching
	wss_skt = socket.socket()
	wss_skt.bind(
		('', 0)
	)

	# Run websockets in a thread for easier manipulations
	wss_thread = threading.Thread(
		target=wss_server,
		args=(wss_skt,)
	)
	wss_thread.start()

	# Run HTTP server in a separate process, because
	# its opinion doesn't matter.
	http_process = multiprocessing.Process(
		target=htserver_process,
		args=(wss_skt.getsockname(),)
	)
	http_process.start()




