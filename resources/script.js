window.self = null;

window.extq = {};



// ===============
//      Util
// ===============
const remap_cls = function(self){
	const prop_names = Object.getOwnPropertyNames(self.constructor.prototype);

	for (const func_name of prop_names){
		if ( (func_name == 'constructor') || func_name.startsWith('$')){continue};

		const original_func = self[func_name];

		if (original_func.constructor.name == 'AsyncFunction'){
			self[func_name] = async function(){
				return await original_func(self, ...arguments)
			}
		}

		if (original_func.constructor.name == 'Function'){
			self[func_name] = function(){
				return original_func(self, ...arguments)
			}
		}

		if (original_func.constructor.name == 'GeneratorFunction'){
			self[func_name] = function(){
				return original_func(self, ...arguments)
			}
		}
	}

	// Experimental: getters and setters
	const gs_dict = {
		// 'getters': {},
		// 'setters': {},
	}

	for (const func_name of prop_names){
		if ( (func_name == 'constructor') || !func_name.startsWith('$') ){continue};

		const real_func_name = func_name.replaceAll('$', '');

		if (!(real_func_name in gs_dict)){
			gs_dict[real_func_name] = {};
		}

		const func = self[func_name];

		if (func_name.startsWith('$$')){
			gs_dict[real_func_name]['set'] = function(){
				return func(self, ...arguments)
			}
			self[func_name] = undefined;
			continue
		}

		if (func_name.startsWith('$')){
			gs_dict[real_func_name]['get'] = function(){
				return func(self, ...arguments)
			}
			self[func_name] = undefined;
			continue
		}
	}

	for (const real_func_name in gs_dict){
		Object.defineProperty(
			self,
			real_func_name,
			gs_dict[real_func_name]
		)
	}

	return self
}

const direct_promise = function(){
	promise_data = {};
	promise_data.promise = new Promise((resolve, reject) => {
		promise_data.resolve = resolve
	});

	return promise_data;
}

const tplate_index = function(tplate_selector, idx_dict){
	const tplate = document.querySelector(tplate_selector).content.cloneNode(true);
	const indexed = {
		'root': tplate.firstElementChild,
	}
	for (sel_name in idx_dict){
		indexed[sel_name] = tplate.querySelector(idx_dict[sel_name]);
	}

	return indexed
}

const apply_attrs = function(dom_elem, attr_data){
	for (const attr_name in attr_data){
		dom_elem.setAttribute(
			attr_name,
			attr_data[attr_name]
		)
	}
}



// ===============
//     Classes
// ===============
const WSSGateway = class{
	constructor(cmd_index){
		const self = remap_cls(this);

		self.ws = null;

		self._ws_url = null;

		self.cmd_index = cmd_index;
	}

	$ws_url(self){
		if (self._ws_url){
			return self._ws_url
		}
		self._ws_url = document.querySelector('body').getAttribute('wss_url');
		return self._ws_url;
	}

	async _open(self){
		const lock = direct_promise();
		self.ws = new WebSocket(self.ws_url);

		self.ws.addEventListener('open', (event) => {
			self.run_cmd('init', 'init');
			lock.resolve();
		});

		self.ws.addEventListener('message', async function(event){
			self.read_cmd(
				await event.data.text()
			)
		});
	}

	async open(self){
		return new Promise((resolve, reject) => {
			self.ws = new WebSocket(self.ws_url);

			self.ws.addEventListener('open', (event) => {
				self.run_cmd('init', 'init');
				resolve(true);
			});

			self.ws.addEventListener('message', async function(event){
				self.read_cmd(
					await event.data.text()
				)
			});
		});
	}

	run_cmd(self, tgt_cmd, data){
		const cmd = {
			'cmd': tgt_cmd,
			'val': data,
		}
		self.ws.send(new Blob([
			JSON.stringify(cmd, null, 2)
		]))
	}

	read_cmd(self, cmd_data){
		// console.log('Message from server', event.data);
		const msg = JSON.parse(cmd_data);
		console.log('recv msg:', msg);

		if (!msg.cmd in self.cmd_index){
			console.warn('CMD', msg.cmd, 'Not found')
		}else{
			self.cmd_index[msg.cmd](msg.val)
		}
	}
}


const PageCounter = class{
	constructor(){
		const self = remap_cls(this);

		self.current = 0;
		self.total = 0;

		self.hits = 0;

		self.counter_dom = document.querySelector('#current_page_num');
		self.hits_dom = document.querySelector('#results_count');
	}

	redraw(self){
		self.counter_dom.innerText = `${self.current}/${self.total}`;
		self.hits_dom.innerText = `${self.hits}`;
	}
}


const MediaItem = class{
	constructor(data){
		const self = remap_cls(this);

		self.preview = data.preview;
		self.full = data.fullres;
		self.mtype = data.media_type;
		self.db_idx = data.idx;

		self.dom = tplate_index(
			'#post_entry_index',
			{
				'preview_img': '.preview_image',
				'icon_img': '.special_icon',
			}
		);
		self.dom.preview_img.src = self.preview;

		self.redraw_type_icon();
		self.bind();
	}

	redraw_type_icon(self){
		if (self.mtype == 'vid'){
			self.dom.icon_img.src = '/resources/video_icon.svg';
			self.dom.icon_img.classList.remove('vis_hidden');
		}

		if (self.mtype == 'flash'){
			self.dom.preview_img.src = '/resources/flash_player.png';
		}

		if (self.mtype == 'img_anim'){
			self.dom.icon_img.src = '/resources/img_anim_icon.svg';
			self.dom.icon_img.classList.remove('vis_hidden');
		}
	}

	open_fullres(self){
		window.extq.maxres_overlay.open_with(self.full, self.mtype);
	}

	request_details(self){
		for (const rm of document.querySelectorAll('#img_pool .post_entry')){
			rm.classList.remove('selected_post');
		}
		self.dom.root.classList.add('selected_post');
		window.extq.ws.run_cmd('get_post_info', self.db_idx);
	}

	bind(self){
		self.dom.root.onclick = function(){
			self.open_fullres();
		};

		self.dom.root.oncontextmenu = function(evt){
			if (evt.altKey){return};
			evt.preventDefault();
			self.request_details();
		};
	}
}


const Paginator = class{
	constructor(){
		const self = remap_cls(this);
		self.media_pool = document.querySelector('#img_pool');
	}

	display_post_details(self, data){
		const tag_list_dom = document.querySelector('#post_info #post_info_tags');
		tag_list_dom.innerHTML = '';
		for (const tag_text of data.tags){
			const tplate = tplate_index(
				'#post_tag_template',
				{
					'tag_text': '.post_tag_entry',
				}
			);
			tplate.tag_text.innerText = tag_text;
			tag_list_dom.append(tplate.root)
		}

		const link_dom = document.querySelector('#link_to_e621_page');
		link_dom.classList.remove('vis_hidden');
		link_dom.href = data.post_link;
	}

	list_page(self, data){
		self.media_pool.innerHTML = '';

		if (data.for_page != window.extq.page_counter.current){
			console.warn(
				`Listing for a wrong page:`,
				data.for_page,
				'while current is:',
				window.extq.page_counter.current
			);
			return
		}

		for (const item of data.items){
			const media_item = new MediaItem(item);
			self.media_pool.append(media_item.dom.root);
		}

		self.media_pool.scrollTop = 0;
	}

	switch_page(self, switch_to){
		const extq = window.extq;
		const page_counter = extq.page_counter;

		if (switch_to?.jump_to || switch_to?.jump_to == 0){
			page_counter.current = parseInt(switch_to.jump_to);
		}else{
			page_counter.current += switch_to.offs;
		}

		page_counter.current = Math.min(
			Math.max(page_counter.current, 0),
			page_counter.total
		);

		page_counter.redraw();

		extq.ws.run_cmd('list_page', page_counter.current);
	}

	next_page(self){
		self.switch_page({'offs': 1});
	}

	prev_page(self){
		self.switch_page({'offs': -1});
	}
}


const ProgBar = class{
	constructor(filler_dom, linked_text=null){
		const self = remap_cls(this);
		self.filler_dom = filler_dom;
		self.linked_text = linked_text;

		self.set_prog(0.0);
	}

	set_prog(self, prog){
		if (prog <= 0.0){
			self.filler_dom.classList.add('vis_hidden');
		}else{
			self.filler_dom.classList.remove('vis_hidden');
		}

		self.filler_dom.style.width = `${100 * prog}%`;
	}

	set_text(self, text){
		self.linked_text.innerText = text;
	}
}


const ChunkedProgbar = class{
	constructor(chunk_amount=null){
		const self = remap_cls(this);
		self.bars = [];
	}

	$$chunk_amount(self, count){
		for (const [dom, bar] of self.bars){
			dom.remove();
		}

		self.bars.length = 0;

		let i = 0;
		while (i < count){
			i++;

			const tplate = tplate_index(
				'#progbar_chunk_tplate',
				{
					'prog': '.progbar_chunk_prog',
				}
			);

			self.bars.push([
				tplate.root,
				new ProgBar(tplate.prog)
			]);
		}
	}

	update_prog(self, bar_idx, prog){
		self.bars[bar_idx][1].set_prog(prog);
	}
}


const MaxResOverlay = class{
	constructor(dialog_selector){
		const self = remap_cls(this);

		self.modal = document.querySelector(dialog_selector);

		self.img = self.modal.querySelector('img');
		self.vid = self.modal.querySelector('video');

		self.shown = false;

		self.playing_video = false;

		self.bind();
	}

	open_with(self, media_url, media_type){
		self.shown = false;
		self.img.classList.add('vis_hidden');
		self.vid.classList.add('vis_hidden');

		if (['img', 'img_anim'].includes(media_type)){
			self.img.src = media_url;
			self.img.classList.remove('vis_hidden');
			self.modal.showModal();
			self.shown = true;
			return
		}

		if (media_type == 'vid'){
			self.vid.src = media_url;
			self.vid.classList.remove('vis_hidden');
			self.modal.showModal();
			self.shown = true;
			self.playing_video = true;
			return
		}
	}

	close(self){
		self.modal.close();
		self.img.src = '';
		self.vid.src = '';
		self.playing_video = false;
		self.shown = false;
	}

	bind(self){
		self.modal.onclick = function(){
			if (!self.playing_video){
				self.close();
			}
		}

		document.addEventListener('keydown', evt => {
			if (evt.key == 'Escape' && !evt.repeat){
				self.close()
			}
		});

		self.bind = null;
	}

}


const QuickSort = class{
	btn_dict = {
		'#sort_by_rating': 'score',
		'#sort_by_newest': 'newest',
		'#sort_by_oldest': 'oldest',
		'#sort_by_videos': 'videos',
		'#sort_by_anims':  'anims',
		'#sort_by_images': 'images',

		// Rating
		'#sort_by_rating_s': 'rating_s',
		'#sort_by_rating_q': 'rating_q',
		'#sort_by_rating_e': 'rating_e',
	}

	constructor(){
		const self = remap_cls(this);
		self.bind();
	}

	bind(self){
		for (const [selector, criteria] of Object.entries(self.btn_dict)){
			document.querySelector(selector).onclick = function(){
				window.extq.ws.run_cmd('quick_sort', {
					'sort_by':      criteria,
					'current_page': window.extq.page_counter.current,
				})
			}
		}
	}
}


const SidebarButtons = class{
	constructor(btn_dict){
		const self = remap_cls(this);
		self.btn_dict = btn_dict;
		self.bind();
	}

	bind(self){
		for (const [sel, func] of Object.entries(self.btn_dict)){
			document.querySelector(sel).onclick = function(evt){
				func(evt)
			}
		}
	}
}







// ======================
//  Middleware functions
// ======================

const empty_media_pool_dom = function(){
	document.querySelector('#img_pool').innerHTML = '';
}

const redownload_database_export = function(){
	empty_media_pool_dom();
	window.extq.chunked_progbar.chunk_amount = 0;
	window.extq.ws.run_cmd('recook_db');
}

const exec_query = function(){
	empty_media_pool_dom();

	window.extq.ws.run_cmd('exec_query');

	window.extq.page_counter.current = 0;
	window.extq.page_counter.redraw();
}

const go_to_page = function(){
	const input_val = parseInt(document.querySelector('#gotopage_input').value);
	if (!input_val && input_val != 0){
		return
	}

	window.extq.paginator.switch_page({'jump_to': input_val});
}

const upd_hit_count = function(data){
	window.extq.page_counter.hits = data.items;
	window.extq.page_counter.total = data.pages;
	window.extq.page_counter.redraw();
}

const force_update_curpage = function(data){
	console.log('??????', data)
	window.extq.page_counter.current = data;
	window.extq.page_counter.redraw();
}

const update_chunked_progbar_count = function(data){
	window.extq.chunked_progbar.chunk_amount = data;
	for (const [dom, progbar] of window.extq.chunked_progbar.bars){
		document.querySelector('#chunked_prog').append(dom);
	}
}









// ======================
//         Init
// ======================


const WSS_CMD_INDEX = Object.freeze({
	'update_global_progress':  (v) => {window.extq.main_progbar.set_prog(v)},
	'upd_prog_text':           (v) => {window.extq.main_progbar.set_text(v)},
	'list_page':               (v) => {window.extq.paginator.list_page(v)},
	'upd_hit_count':           upd_hit_count,
	'show_tags':               (v) => {window.extq.paginator.display_post_details(v)},
	'upd_progbar_count':       update_chunked_progbar_count,
	'update_chunked_progress': (v) => {window.extq.chunked_progbar.update_prog(v.idx, v.prog)},
	'force_update_curpage':    force_update_curpage,
})

const SIDEBAR_BTN_INDEX = Object.freeze({
	'#dl_db_export_btn': redownload_database_export,
	'#exec_query':       exec_query,
	'#next_page':        () => {window.extq.paginator.next_page()},
	'#previous_page':    () => {window.extq.paginator.prev_page()},
	'#gotopage_btn':     go_to_page,
})

const main = async function(){
	window.extq.main_progbar = new ProgBar(
		document.querySelector('#curprog_fill'),
		document.querySelector('#curprog_text')
	)

	window.extq.maxres_overlay = new MaxResOverlay('#fullres_overlay');

	window.extq.chunked_progbar = new ChunkedProgbar();

	window.extq.paginator = new Paginator();

	window.extq.page_counter = new PageCounter();


	window.extq.ws = new WSSGateway(WSS_CMD_INDEX);
	await window.extq.ws.open();

	window.extq.sidebar_btns = new SidebarButtons(SIDEBAR_BTN_INDEX);

	window.extq.quick_sort = new QuickSort();

	// window.extq.paginator.switch_page({'jump_to': 0});

	window.extq.ws.run_cmd('restore_saved_page');



	document.addEventListener('keydown', evt => {
		if (evt.repeat){return};
		if (evt.which == 83 && evt.ctrlKey){
			evt.preventDefault();

			window.extq.ws.run_cmd('save_game', window.extq.page_counter.current)
		}
	});
}

main()