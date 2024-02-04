
window.curpage = 0;
window.total_pages = 0;
window.video_overlay_on = false;



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


const progress_bar = new ProgressBar()
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



const wss_con = new WebSocket(
	document.querySelector('body').getAttribute('wss_url')
);

wss_con.addEventListener('open', (event) => {
	wss_con.send('{"cmd": "Hello"}');

	const cmd = {
		'cmd': 'list_page',
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
		media_tplate.root.setAttribute('fullres', full);
		media_tplate.root.setAttribute('media_type', mtype);

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

		tgt_container.append(media_tplate.root);
	}

	tgt_container.scrollTop = 0;
}





const update_hit_count = function(data){
	document.querySelector('#results_count').innerText = `Hit count: ${data.items}`;
	window.total_pages = data.pages;
	update_page_counter()
}

const update_page_counter = function(){
	document.querySelector('#current_page_num').innerText = `${window.curpage}/${window.total_pages}`;
}


wss_con.addEventListener('message', async function(event){
	// console.log('Message from server', event.data);
	const msg = JSON.parse(await event.data.text());
	console.log('recv msg:', msg)

	if (msg.cmd == 'update_progress'){
		progress_bar.set_prog(100 * msg.val)
	}
	if (msg.cmd == 'upd_prog_text'){
		progress_bar.set_bar_text(msg.val)
	}
	if (msg.cmd == 'list_page'){
		list_page(msg.val)
	}
	if (msg.cmd == 'upd_hit_count'){
		update_hit_count(msg.val)
	}
});


document.querySelector('#dl_db_export_btn').onclick = function(){
	const cmd = {
		'cmd': 'dl_db_export_btn',
	}
	const blob = new Blob(
		[JSON.stringify(cmd, null, 2)]
	);
	wss_con.send(blob)
}


document.querySelector('#exec_query').onclick = function(){
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


