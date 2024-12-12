import multiprocessing
from multiprocessing import freeze_support

import threading
import socket
import json
import time
import requests
import gzip
import shutil
import struct
import csv
import importlib
import pickle
import math
import sys
from min_http import MinHTTP
from min_wss import MinWSession
from pathlib import Path
from bs4 import BeautifulSoup as jquery
from datetime import datetime

from queue import Queue

from db_sys import (
	DBCooker,
	TagCooker,
	ChunkedDB,
	QuickSortCriterias,

	# File type maps
	MD_VIDEO,
	MD_FLASH,
	MD_IMG,
	MD_IMG_ANIMATED,

	# Paths
)

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

def freeze():
	while True:
		time.sleep(0.1)

# print('fpath', __file__)


# Some constants
INTERNAL_RES_PATH = None

# Have a better idea?
# Know how to achieve this without using any rubbish
# frameworks or complex mechanisms?
# Please comment on github.
# (This script has to behave differently depending on
# whether it's a compiled exe or not)
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








# ============================
#             Util
# ============================
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



# ============================
#           The shit
# ============================


def htserver_process(wss_port):
	from htpage_serv import htserver
	htserver(wss_port)

def wss_server(skt, extq):
	skt.listen(2)
	print('WSS Started')
	while True:
		try:
			conn, address = skt.accept()
			wss_session(MinWSession(conn), extq)
		except Exception as e:
			print_exception(e)
			continue

def wss_session(wsession, extq):
	try:
		extq.progbars.wsession = wsession
		extq.wsession = wsession
		# Index WSS commands
		wss_cmd_dict = {}
		for cmd_tgt in CMD_REGISTRY:
			wss_cmd_dict[cmd_tgt.wss_cmd] = cmd_tgt


		if COOKED_DB_FPATH.is_file():
			wsession.send_json({
				'cmd': 'upd_hit_count',
				'val': {
					'items': len(extq.db.filtered_index),
					'pages': extq.page_count,
				},
			})

			extq.progbars.update_count()

			if extq.current_page:
				wsession.send_json({
					'cmd': 'force_update_curpage',
					'val': extq.current_page,
				})
		else:
			extq.progbars.update_text(
				'Download the database before searching'
			)

	except Exception as e:
		print_exception(e)
		return

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
				cmd_class = wss_cmd_dict[wss_cmd['cmd']](wsession, extq)
				cmd_class.execute(wss_cmd.get('val'))

		except Exception as e:
			print_exception(e)
			return


class ProgressBars:
	def __init__(self, wsession, extq=None):
		self.extq = extq
		self.wsession = wsession

	def update_count(self):
		self.wsession.send_json({
			'cmd': 'upd_progbar_count',
			'val': len(self.extq.db.chunks),
		})

	def update_global(self, prog, with_text=None):
		if with_text:
			self.update_text(with_text)

		self.wsession.send_json({
			'cmd': 'update_global_progress',
			'val': prog,
		})

	def update_chunked(self, prog, idx, with_text=None):
		if with_text:
			self.update_text(with_text)

		self.wsession.send_json({
			'cmd': 'update_chunked_progress',
			'val': {
				'idx': idx,
				'prog': prog,
			},
		})

	def update_text(self, text):
		self.wsession.send_json({
			'cmd': 'upd_prog_text',
			'val': str(text),
		})


class EXTQ:

	CACHED_COOKING = False

	ITEMS_PER_PAGE = 80

	def __init__(self):
		self._db = None
		self._progbars = None

		self.wsession = None

		self.current_page = 0

	@property
	def progbars(self):
		if self._progbars:
			return self._progbars

		self._progbars = ProgressBars(self.wsession, self)

		return self._progbars

	def recook_db(self):
		try:
			self._db.terminate()
		except: pass

		cbacks = {
			'dl': (
				lambda prog: self.progbars.update_global(
					prog,
					'Downloading the database...'
				)
			),
			'cook': (
				lambda prog: self.progbars.update_global(
					prog,
					'Cooking the database...'
				)
			)
		}

		with DBCooker(True, False, callbacks=cbacks, cached=self.CACHED_COOKING) as db_cooker:
			with open(COOKED_DB_FPATH, 'wb') as tgt_file:
				pickle.dump(
					db_cooker.cooked_db,
					tgt_file,
					protocol=pickle.HIGHEST_PROTOCOL
				)

			self._db = ChunkedDB(
				db_cooker.cooked_db,
				prog_callback=(
					lambda worker, prog: self.progbars.update_chunked(
						prog,
						self.db.chunks.index(worker)
					)
				),
				worker_init_callback=(
					lambda prog: self.progbars.update_global(
						prog,
						'Initializing...'
					)
				)
			)


		self.progbars.update_count()

		# self._db.run_filter()

		return self._db

	@property
	def db(self):
		if self._db:
			return self._db

		if COOKED_DB_FPATH.is_file():
			self.progbars.update_text('Loading last save, please wait...')
			with open(COOKED_DB_FPATH, 'rb') as tgt_file:
				self._db = ChunkedDB(
					pickle.load(tgt_file),
					prog_callback=(
						lambda worker, prog: self.progbars.update_chunked(
							prog,
							self.db.chunks.index(worker)
						)
					),
					worker_init_callback=(
						lambda prog: self.progbars.update_global(
							prog,
							'Initializing...'
						)
					)
				)
		else:
			self.recook_db()

		if GAMESAVE_FPATH.is_file():
			with open(GAMESAVE_FPATH, 'rb') as tgt_file:
				save_data = pickle.load(tgt_file)
				self._db.apply_saved_state(save_data)

			if self._db.filtered_index and save_data['extras']:
				self.current_page = save_data['extras'].get('page')

		self.progbars.update_count()

		return self._db

	@property
	def page_count(self):
		# todo:
		return math.floor(
			(len(self.db.filtered_index) - 1) / self.ITEMS_PER_PAGE
		)

	def run(self):
		# The HTTP server needs to know the socket WSS is running on,
		# before launching
		wss_skt = socket.socket()
		wss_skt.bind(
			('', 0)
		)

		# Run websockets in a thread for easier manipulations
		wss_thread = threading.Thread(
			target=wss_server,
			args=(wss_skt, self,)
		)
		wss_thread.start()

		# Run HTTP server in a separate process, because
		# its opinion doesn't matter.
		http_process = multiprocessing.Process(
			target=htserver_process,
			args=(wss_skt.getsockname(),)
		)
		http_process.start()




class GetPostInfo:
	wss_cmd = 'get_post_info'

	def __init__(self, wsession, extq):
		self.wsession = wsession
		self.extq = extq

	def execute(self, post_idx):
		if post_idx > (len(self.extq.db.filtered_index) - 1):
			return

		record = self.extq.db.get_post_info(post_idx)

		self.wsession.send_json({
			'cmd': 'show_tags',
			'val': {
				'tags': list(record['tag_string']),
				# 'full': ExtendedQuery.pipe_struct(q_session.query_cache[post_idx]),
				'full': {},
				# todo: this will become onsolete once 'full' is present
				'post_link': f"""https://e621.net/posts/{record['id']}""",
			},
		})


class CacheQuickSort:
	wss_cmd = 'quick_sort'

	def __init__(self, wsession, extq):
		self.wsession = wsession
		self.extq = extq

		self.sorting_types = {
			'score':  QuickSortCriterias.score_criteria,
			'newest': QuickSortCriterias.newest_criteria,
			'oldest': QuickSortCriterias.oldest_criteria,
			'videos': QuickSortCriterias.videos_criteria,
			'anims':  QuickSortCriterias.anims_criteria,
			'images': QuickSortCriterias.images_criteria,

			# Rating
			'rating_s': QuickSortCriterias.rating_s_criteria,
			'rating_q': QuickSortCriterias.rating_q_criteria,
			'rating_e': QuickSortCriterias.rating_e_criteria,
		}

	def execute(self, data):
		tgt_func = self.sorting_types.get(data.get('sort_by'))

		if not tgt_func:
			self.wsession.send_json({
				'cmd': 'upd_prog_text',
				'val': (
					f"""Minor misunderstanding: """
					"""Sorting criteria "{data.get('sort_by')}" is invalid"""
				),
			})
			return

		for i in range(len(self.extq.db.chunks)):
			self.extq.progbars.update_chunked(0.0, i)

		self.extq.db.quick_sort.run(tgt_func)

		GameSave(self.wsession, self.extq).execute()

		page_lister = PageLister(self.wsession, self.extq)
		page_lister.list_page(
			data.get('current_page', 0)
		)


class PageLister:
	wss_cmd = 'list_page'

	def __init__(self, wsession, extq):
		self.wsession = wsession
		self.extq = extq

	def execute(self, page_idx):
		self.list_page(page_idx)

	@staticmethod
	def get_media_type(db_record):
		# todo: better way of doing this
		# such as static defines
		type_dict = (
			(MD_VIDEO, 'vid'),
			(MD_FLASH, 'flash'),
			# todo: fuck
			(MD_IMG_ANIMATED, 'img_anim'),
			(MD_IMG, 'img'),
		)

		for ext, media_type in type_dict:
			if db_record['file_ext'] in ext:
				return media_type

	def list_page(self, PAGE_IDX, from_latest=False):
		PAGE_COUNT = self.extq.page_count
		PAGE_OFFSET = EXTQ.ITEMS_PER_PAGE * PAGE_IDX
		CACHE_LEN = len(self.extq.db.filtered_index) - 1

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
		record_idx = PAGE_OFFSET

		while len(media_items) < EXTQ.ITEMS_PER_PAGE and record_idx <= CACHE_LEN and record_idx >= 0:
			record = self.extq.db.get_post_info(record_idx)

			rhash = record['md5']
			r_ext = record['file_ext']

			media_item_data = {
				'preview': f'https://static1.e621.net/data/preview/{rhash[0:2]}/{rhash[2:4]}/{rhash}.jpg',
				'fullres': f'https://static1.e621.net/data/{rhash[0:2]}/{rhash[2:4]}/{rhash}.{r_ext}',
				'media_type': self.get_media_type(record),
				'idx': record_idx,
				'db_id': record['id'],
				'score': record['score'],
				'rating': record['rating'],
			}

			# media_items.insert(0, media_item_data)
			media_items.append(media_item_data)
			record_idx += 1

		self.wsession.send_json({
			'cmd': 'list_page',
			'val': {
				'for_page': PAGE_IDX,
				'items': media_items,
			},
		})


class RestoreSavedPage:
	wss_cmd = 'restore_saved_page'

	def __init__(self, wsession, extq):
		self.wsession = wsession
		self.extq = extq

	def execute(self, _):
		# print('Restoring saved page?', self.extq.current_page)
		# if self.extq.current_page:
		if self.extq._db:
			PageLister(self.wsession, self.extq).execute(
				self.extq.current_page or 0
			)


class ExtendedQuery:
	wss_cmd = 'exec_query'

	def __init__(self, wsession, extq):
		self.wsession = wsession
		self.extq = extq

	def execute(self, *args):
		GAMESAVE_FPATH.unlink(missing_ok=True)
		self.extq.progbars.update_text('Running query...')
		self.extq.db.run_filter()

		self.wsession.send_json({
			'cmd': 'upd_hit_count',
			'val': {
				'items': len(self.extq.db.filtered_index),
				'pages': self.extq.page_count,
			},
		})

		if len(self.extq.db.filtered_index) <= 0:
			self.extq.progbars.update_text('Search returned nothing')
			return

		CacheQuickSort(self.wsession, self.extq).execute({
			'sort_by': 'newest'
		})

		GameSave(self.wsession, self.extq).execute()

		page_lister = PageLister(self.wsession, self.extq)
		page_lister.list_page(0)


class ReCooker:
	wss_cmd = 'recook_db'

	def __init__(self, wsession, extq):
		self.wsession = wsession
		self.extq = extq

	def execute(self, _):
		self.extq.progbars.update_text('Cooking the Database')
		self.extq.recook_db()
		# page_lister = PageLister(self.wsession, self.extq).list_page(0)
		# CacheQuickSort(self.wsession, self).execute({
		# 	'sort_by': 'newest'
		# })

		self.extq.progbars.update_text('Database cooked. Search enabled')

class GameSave:
	wss_cmd = 'save_game'

	def __init__(self, wsession, extq):
		self.wsession = wsession
		self.extq = extq

	def execute(self, page=None):
		self.extq.current_page = page or 0
		self.extq.progbars.update_global(0.0)
		self.extq.db.save_state(GAMESAVE_FPATH, {
			'page': page,
		})

		self.extq.progbars.update_global(1.0, 'Saved Current State...')


CMD_REGISTRY = (
	CacheQuickSort,
	GetPostInfo,
	PageLister,
	ExtendedQuery,
	ReCooker,
	GameSave,
	RestoreSavedPage,
)


def main():
	if IS_EXE and (not (THISDIR / 'tag_match.py').is_file()):
		shutil.copy(
			INTERNAL_RES_PATH / 'resources' / 'tag_match_sample.py',
			THISDIR / 'tag_match.py',
		)

	extq_main = EXTQ()
	extq_main.run()

	freeze()

if __name__ == '__main__':
	freeze_support()
	main()


