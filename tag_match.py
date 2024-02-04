
tgmatch = {

	# A post MUST contain ALL of these, otherwise - reject
	'yes': [
		# 'scalie',
		# 'lactating',
		# 'alcohol',
		# 'asdasdasd',
		# 'hetero',
		# 'smoking',
	],
	# additive is only used when 'yes' is not empty
	# it means that the post should also contain any of the 'perhaps'
	# actually, this should be always on
	# (for best sorting results)
	'additive': 'yes',

	# Find posts that contain at least ONE of these
	'perhaps': [
		'reptile',
		'lizard',
		'dragon',
		'dinosaur',
		# 'anthro',
		'scalie',
		'snake',
		'xenomorph',
		'alien_(franchise)',
	],

	# 'flash'
	# 'video'
	# 'image'
	# 'animated_image'
	'of_type': None,

	# A post must contain NONE of these
	'no': [
		'gore',
		'vore',
		'overweight',
		'loli',

		'chica_(fnaf)',
		'bony_(fnaf)',
		'fasbear_(fnaf)',
		'foxy_(fnaf)',
		'fnaf',

		'oviposition',
		'pregnant',
		'pregnant_male',
		'pregnant_female',
		'kung_fu_panda',
		'master_po_ping',
		'belly_inflation',
		'hyper',
		'turtle',
		'split_form',
		'lamia',
		'pukao',

		'monster_girl_(genre)',
		'kenkou_cross',

		'fernando_faria',

	],

	# How this works:
	# A post has 3 tags:
	# chica_(fnaf)  bony_(fnaf)  fasbear_(fnaf)

	# IF any text from below matches like this:
	# chica_(fnaf)  bony_(fnaf)  applejack_(mlp)
	#      ^^^^^^^       ^^^^^^            ^^^^^
	#      _(fnaf)       (fnaf)            (mlp)

	# Then - skip

	'partial': [
		'(fnaf)',
		'(mlp)',
		'kung_fu_panda',
		'master_po',
		'(tmnt)',
		'teenage_mutant_ninja_turtles',
		'devin',
		'faolan'
		'(kitora)',
		'(onta)',
		'shrek',
		'nidoran',
	]
}


