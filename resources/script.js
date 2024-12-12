
// Yes, it's a mess.
// Should work via classes.
// For now - it just works.
// Classes will come once they're actually needed.

window.self = null;
window.curpage = 0;
window.total_pages = 0;
window.video_overlay_on = false;
window.chunk_bars = [];



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


const toggle_btn = function(qsel, state){
	const btn = document.querySelector(qsel);

	if (state == true){
		btn.classList.add('btn_disabled');
	}

	if (state == false){
		btn.classList.remove('btn_disabled');
	}
}



const ProgressBar = class{
	constructor(){
		this.bar_text = document.querySelector('#curprog_text');
		this.bat_fill = document.querySelector('#curprog_fill');
	}

	set_prog(prog){
		this.bat_fill.style.width = `${prog}%`;
	}

	set_bar_text(btext){
		this.bar_text.innerText = btext;
	}
}

const DynamicProgBar = class{
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


const progress_bar = new DynamicProgBar(
	document.querySelector('#curprog_fill'),
	document.querySelector('#curprog_text')
);
const overlay_modal = document.querySelector('#fullres_overlay');
const fullres_img = document.querySelector('#fullscreen_preview_img');
const fullres_vid = document.querySelector('#fullscreen_preview_video');

overlay_modal.onclick = function(){
	if (!window.video_overlay_on){
		overlay_modal.close();
		fullres_img.src = '';
		fullres_vid.src = '';
		window.video_overlay_on = false;
	}
}

document.addEventListener('keydown', evt => {
	if (evt.key == 'Escape' && !evt.repeat){
		overlay_modal.close();
		fullres_img.src = '';
		fullres_vid.src = '';
		window.video_overlay_on = false;
	}
	if (evt.key == '1' && evt.altKey && !evt.repeat){
		wss_con.close()
	}
});


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



const wss_con = new WebSocket(
	document.querySelector('body').getAttribute('wss_url')
);

wss_con.addEventListener('open', (event) => {
	wss_con.send('{"cmd": "Hello"}');

	const cmd = {
		'cmd': 'restore_saved_page',
		'val': window.curpage,
	}
	const blob = new Blob(
		[JSON.stringify(cmd, null, 2)]
	);
	wss_con.send(blob)
});


const open_fullres_overlay = function(media_url, media_type){
	fullres_img.classList.add('vis_hidden');
	fullres_vid.classList.add('vis_hidden');


	if (media_type == 'img'){
		fullres_img.src = media_url;
		fullres_img.classList.remove('vis_hidden');
		overlay_modal.showModal();
		return
	}

	if (media_type == 'vid'){
		fullres_vid.src = media_url;
		fullres_vid.classList.remove('vis_hidden');
		overlay_modal.showModal();
		window.video_overlay_on = true;
		return
	}

	if (media_type == 'img_anim'){
		fullres_img.src = media_url;
		fullres_img.classList.remove('vis_hidden');
		overlay_modal.showModal();
		return
	}
}


const show_post_info = function(data){
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

	link_dom = document.querySelector('#link_to_e621_page');
	link_dom.classList.remove('vis_hidden');
	link_dom.href = data.post_link;

	/*
	const attr_list_dom = document.querySelector('#post_info #post_into_attributes');
	attr_list_dom.innerHTML = '';

	for (const attr_label in data.attrs){
		const tplate = tplate_index(
			'#post_info_attribute_template',
			{
				'label': '.attr_label',
				'value': '.attr_value',
			}
		);

		tplate.label.innerText = attr_label;
		tplate.value.innerText = data.attrs[attr_label];

		attr_list_dom.append(tplate.root);
	}
	*/
}


const list_page = function(data){
	const tgt_container = document.querySelector('#img_pool');
	tgt_container.innerHTML = '';

	if (data.for_page != window.curpage){
		console.log('Listing for a wrong page')
		return
	}

	for (const item of data.items){
		const preview = item.preview;
		const full = item.fullres;
		const mtype = item.media_type;

		// const media_node = document.createElement('img');
		const media_tplate = tplate_index(
			'#post_entry_index',
			{
				'preview_img': '.preview_image',
				'icon_img': '.special_icon',
			}
		);

		media_tplate.preview_img.src = preview;
		apply_attrs(
			media_tplate.root,
			{
				'fullres':    full,
				'media_type': mtype,
				'db_id':      item.db_id,
				'score':      item.score,
				'rating':     item.rating,
			}
		)

		if (mtype == 'vid'){
			media_tplate.icon_img.src = '/resources/video_icon.svg';
			media_tplate.icon_img.classList.remove('vis_hidden');
		}

		if (mtype == 'flash'){
			media_tplate.preview_img.src = '/resources/flash_player.png';
		}

		if (mtype == 'img_anim'){
			media_tplate.icon_img.src = '/resources/img_anim_icon.svg';
			media_tplate.icon_img.classList.remove('vis_hidden');
		}

		media_tplate.root.onclick = function(){
			open_fullres_overlay(full, mtype)
		};

		media_tplate.root.oncontextmenu = function(evt){
			if (evt.altKey){return};
			evt.preventDefault();

			for (const rm of document.querySelectorAll('#img_pool .post_entry')){
				rm.classList.remove('selected_post');
			}

			media_tplate.root.classList.add('selected_post');

			const cmd = {
				'cmd': 'get_post_info',
				'val': item.idx,
			}
			const blob = new Blob(
				[JSON.stringify(cmd, null, 2)]
			);
			wss_con.send(blob)
		};

		tgt_container.append(media_tplate.root);
	}

	tgt_container.scrollTop = 0;
}


const force_update_curpage = function(data){
	window.curpage = data;
	update_page_counter()
}


const update_hit_count = function(data){
	document.querySelector('#results_count').innerText = `Results: ${data.items}`;
	window.total_pages = data.pages;
	update_page_counter()
}

const update_page_counter = function(){
	document.querySelector('#current_page_num').innerText = `${window.curpage}/${window.total_pages}`;
}


const upd_progbar_count = function(count){
	const chunk_list = document.querySelector('#chunked_prog');
	chunk_list.innerHTML = '';
	window.chunk_bars.length = 0;
	let i = 0;
	while (i < count){
		i++;

		const tplate = tplate_index(
			'#progbar_chunk_tplate',
			{
				'prog': '.progbar_chunk_prog',
			}
		);

		window.chunk_bars.push(
			new DynamicProgBar(tplate.prog)
		);
		chunk_list.append(tplate.root);
	}
}

const update_chunked_progress = function(data){
	window.chunk_bars[data.idx].set_prog(data.prog);
}

const lock_gui = function(state){

}


wss_con.addEventListener('message', async function(event){
	// console.log('Message from server', event.data);
	const msg = JSON.parse(await event.data.text());
	console.log('recv msg:', msg)

	if (msg.cmd == 'update_global_progress'){
		progress_bar.set_prog(msg.val)
	}
	if (msg.cmd == 'upd_prog_text'){
		progress_bar.set_text(msg.val)
	}
	if (msg.cmd == 'list_page'){
		list_page(msg.val)
	}
	if (msg.cmd == 'upd_hit_count'){
		update_hit_count(msg.val)
	}
	if (msg.cmd == 'show_tags'){
		show_post_info(msg.val)
	}
	if (msg.cmd == 'show_tags'){
		show_post_info(msg.val)
	}
	if (msg.cmd == 'upd_progbar_count'){
		upd_progbar_count(msg.val)
	}
	if (msg.cmd == 'update_chunked_progress'){
		update_chunked_progress(msg.val)
	}
	if (msg.cmd == 'force_update_curpage'){
		force_update_curpage(msg.val)
	}
});


document.querySelector('#dl_db_export_btn').onclick = function(){
	document.querySelector('#chunked_prog').innerHTML = '';
	document.querySelector('#img_pool').innerHTML = '';
	const cmd = {
		'cmd': 'recook_db',
	}
	const blob = new Blob(
		[JSON.stringify(cmd, null, 2)]
	);
	wss_con.send(blob)
}


document.querySelector('#exec_query').onclick = function(){
	document.querySelector('#img_pool').innerHTML = '';

	const cmd = {
		'cmd': 'exec_query',
	}
	const blob = new Blob(
		[JSON.stringify(cmd, null, 2)]
	);
	wss_con.send(blob)

	window.curpage = 0;
	update_page_counter()
}



document.querySelector('#next_page').onclick = function(){
	window.curpage += 1;

	update_page_counter()

	const cmd = {
		'cmd': 'list_page',
		'val': window.curpage,
	}
	const blob = new Blob(
		[JSON.stringify(cmd, null, 2)]
	);
	wss_con.send(blob)
}


document.querySelector('#previous_page').onclick = function(){
	window.curpage -= 1;
	window.curpage = Math.max(window.curpage, 0);

	update_page_counter()

	const cmd = {
		'cmd': 'list_page',
		'val': window.curpage,
	}
	const blob = new Blob(
		[JSON.stringify(cmd, null, 2)]
	);
	wss_con.send(blob)
}


document.querySelector('#gotopage_btn').onclick = function(){
	const input_val = document.querySelector('#gotopage_input').value;
	if (!input_val){
		return
	}

	window.curpage = parseInt(input_val);

	update_page_counter()

	const cmd = {
		'cmd': 'list_page',
		'val': window.curpage,
	}
	const blob = new Blob(
		[JSON.stringify(cmd, null, 2)]
	);
	wss_con.send(blob)
}



document.addEventListener('keydown', evt => {
	if (evt.repeat){return};
	if (evt.which == 83 && evt.ctrlKey){
		evt.preventDefault();

		const cmd = {
			'cmd': 'save_game',
			'val': window.curpage,
		}
		const blob = new Blob(
			[JSON.stringify(cmd, null, 2)]
		);
		wss_con.send(blob)
	}
});


const bind_sortings = function(){

	const sort_dict = {
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

	for (const selector in sort_dict){
		const criteria = sort_dict[selector];

		document.querySelector(selector).onclick = function(){
			const cmd = {
				'cmd': 'quick_sort',
				'val': {
					'sort_by':      criteria,
					'current_page': window.curpage,
				},
			}
			const blob = new Blob(
				[JSON.stringify(cmd, null, 2)]
			);
			wss_con.send(blob)
		}
	}

}

bind_sortings()


