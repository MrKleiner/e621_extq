from pathlib import Path
import shutil, subprocess, json, sys

PROJECT = Path(__file__).parent

TMP_DIR = PROJECT / 'tmp'
EXE_OUT_DIR = PROJECT / 'exe_out'
VERSION = '1-1-56'


def pyinst_cleanup(base_name, src_folder, move_to):
	import shutil

	src_folder = Path(src_folder)
	move_to = Path(move_to)

	move_to.unlink(missing_ok=True)

	
	# move executable to the specified destination
	shutil.move(
		src_folder / 'dist' / f'{base_name}.exe',
		move_to,
	)

	# wipe build folder
	shutil.rmtree(src_folder / 'build', ignore_errors=True)
	# remove the dist folder
	shutil.rmtree(src_folder / 'dist', ignore_errors=True)
	# remove the .spec file
	(src_folder / f'{base_name}.spec').unlink(missing_ok=True)


shutil.rmtree(TMP_DIR, ignore_errors=True)
# shutil.rmtree(EXE_OUT_DIR, ignore_errors=True)

EXE_OUT_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)


# Have better ideas how to make a script behave differently
# only after it was turned into an exe?
# Please let me know...
(TMP_DIR / 'main.py').write_bytes(
	(PROJECT / 'main.py').read_bytes().replace(b'@@NOT_EXE', b'is_exe')
)
(TMP_DIR / 'htpage_serv.py').write_bytes(
	(PROJECT / 'htpage_serv.py').read_bytes().replace(b'@@NOT_EXE', b'is_exe')
)


compile_params = [
	str(Path(sys.executable)),

	'-m', 'PyInstaller', 

	'--noconfirm',
	'--onefile',
	'--console',
	'--icon',

	# Icon
	str(PROJECT / 'favicon.ico'),

	# Ignore tag match
	'--exclude-module', 'tag_match',
	'--exclude-module', 'htpage_serv',
	'--exclude-module', 'min_http',
	'--exclude-module', 'min_wss',

	# Resource folder
	'--add-data', str(PROJECT / 'resources;resources/'),

	# Lib
	'--add-data', str(TMP_DIR / 'htpage_serv.py;.'),
	'--add-data', str(PROJECT / 'min_http.py;.'),
	'--add-data', str(PROJECT / 'min_wss.py;.'),
	# '--add-data', str(TMP_DIR / 'tag_match.py;.'),

	# Base script
	str(TMP_DIR / 'main.py'),
]

subprocess.run(compile_params)


pyinst_cleanup(
	'main',
	PROJECT,
	EXE_OUT_DIR / f'e621_extq_{VERSION}.exe'
)

shutil.copy(
	EXE_OUT_DIR / f'e621_extq_{VERSION}.exe',
	EXE_OUT_DIR / 'e621_extq_latest.exe'
)


shutil.rmtree(TMP_DIR, ignore_errors=True)


