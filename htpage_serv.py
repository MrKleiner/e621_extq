from min_http import MinHTTP
from pathlib import Path
import time, sys

IS_EXE = 'is_exe' == '@@NOT_EXE'

def devprint(*args, **kwargs):
	if not IS_EXE:
		print(*args, **kwargs)

THISDIR = Path(__file__).parent

if IS_EXE:
	CUSTOM_JS_PATH = Path(sys.executable).parent / 'custom'
else:
	CUSTOM_JS_PATH = Path(__file__).parent / 'custom'

WEB_RESOURCES_PATH = THISDIR / 'resources'

HTML_PAGE_PATH = WEB_RESOURCES_PATH / 'base_page.html'

CDN_RESOURCE_INDEX = (
	(
		'script.js',
		WEB_RESOURCES_PATH / 'script.js',
		'application/javascript',
	),
	(
		'customjs/special.js',
		CUSTOM_JS_PATH / 'special.js',
		'application/javascript',
	),
	(
		'resources/video_icon.svg',
		WEB_RESOURCES_PATH / 'video_icon.svg',
		'image/svg+xml',
	),
	(
		'resources/flash_player.',
		WEB_RESOURCES_PATH / 'flash_player.png',
		'image/png',
	),
	(
		'/favicon',
		WEB_RESOURCES_PATH / 'favicon.png',
		'image/png',
	),
	(
		'resources/img_anim_icon.',
		WEB_RESOURCES_PATH / 'img_anim_icon.svg',
		'image/svg+xml',
	),
	(
		'style.css',
		WEB_RESOURCES_PATH / 'style.css',
		'text/css',
	),
	(
		'resources/icon_arrow_right.',
		WEB_RESOURCES_PATH / 'icon_arrow_right.svg',
		'image/svg+xml',
	),
	(
		'resources/icon_arrow_left.',
		WEB_RESOURCES_PATH / 'icon_arrow_left.svg',
		'image/svg+xml',
	),
	(
		'resources/alphabet.ttf',
		WEB_RESOURCES_PATH / 'alphabet.ttf',
		'image/svg+xml',
	),
)



def htcallback(cl_request):

	for cdn_query, fpath, mime in CDN_RESOURCE_INDEX:
		if cdn_query in cl_request.path:
			if fpath.is_file():
				cl_request.flush_bytes(
					fpath.read_bytes(),
					mime,
				)
				return
			else:
				cl_request.deny()


	wss_url = f"""ws://127.0.0.1:{cl_request.shared_data['wss_info'][1]}"""
	cl_request.flush_bytes(
		HTML_PAGE_PATH.read_bytes().replace(b'@@wss_url', wss_url.encode()),
		'text/html; charset=utf-8',
	)


def htserver(wss_port):
	mhttp = MinHTTP(
		htcallback,
		{
			'wss_info': wss_port,
		},
		None if IS_EXE else 8089
	)

	print('HTTP Started')
	devprint('HTTP on', 8089)

	if IS_EXE:
		while True:
			time.sleep(0.5)
			if not mhttp.addr_info:
				continue
			print(
				'Type this into your browser:',
				f'http://127.0.0.1:{mhttp.addr_info[1]}'
			)
			break











