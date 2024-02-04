from min_http import MinHTTP
from pathlib import Path

THISDIR = Path(__file__).parent


WEB_RESOURCES_PATH = THISDIR / 'resources'

HTML_PAGE_PATH = WEB_RESOURCES_PATH / 'base_page.html'

CDN_RESOURCE_INDEX = (
	(
		'script.js',
		WEB_RESOURCES_PATH / 'script.js',
		'application/javascript',
	),
	(
		'special.js',
		WEB_RESOURCES_PATH / 'special.js',
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
)



def htcallback(cl_request):

	for cdn_query, fpath, mime in CDN_RESOURCE_INDEX:
		if cdn_query in cl_request.path:
			cl_request.flush_bytes(
				fpath.read_bytes(),
				mime,
			)
			return


	wss_url = f"""ws://127.0.0.1:{cl_request.shared_data['wss_info'][1]}"""
	cl_request.flush_bytes(
		HTML_PAGE_PATH.read_bytes().replace(b'@@wss_url', wss_url.encode()),
		'text/html; charset=utf-8',
	)


def htserver(wss_port):
	MinHTTP(
		htcallback,
		{
			'wss_info': wss_port,
		}
	)

	print('HTTP Started')









