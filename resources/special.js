


document.addEventListener('contextmenu', evt => {
	console.log('What?')
	const target = evt.target.closest('#img_pool .post_entry');
	if (target && evt.altKey){
		target.classList.add('flash')
		// target.classList.remove('flash_out')

		// target.classList.add('flash')
		// target.classList.add('flash_out')

		evt.preventDefault()
		console.log('Tryna fetch...')
		fetch(
			'http://192.168.0.6:8027/cmd?cmd=upload',
			{
				'headers': {
					// 'cache-control': 'no-cache',
					// 'pragma': 'no-cache',
					// 'Access-Control-Allow-Origin': '*',
				},
				'method': 'POST',
				'mode': 'no-cors',
				'credentials': 'omit',
				'cache': 'no-store',
				'body': new Blob([target.getAttribute('fullres')]),
			}
		)
	}
});
















