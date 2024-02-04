
# Basically, posts are filtered by tag groups.
# For now, posts can only be filtered by tags.
# If people find this tool useful - other filtering methods will be added.
# Each group has an explanation of what it does.

# Syntax is as follows:
# The words have to be enclosed in single quotation marks ('')
# and separated by a comma (,)

# There can be any amount of spaces or line breaks between words.
# And there can be any amount of tags to filter by.
# No funny numbers like 4096 or anything. Literally ANY amount.

# Tags are case-sensitive.

# (for those, who know: yes, "" is acceptable too, but fuck them really)


# It's possible to "disable" a certain tag, by adding "#" to the
# beginning of the line.

# Basically, any line that has "#" in the beginning is completely
# ignored by the software, at all times.

# Notepad++ has a default bind "Ctrl+Q" to automatically
# insert/remove "#".



tgmatch = {

	# A post MUST contain ALL of these, otherwise - reject
	'yes': [
		'lizard',
		'alcohol',
	],

	# Additive is only used when 'yes' is not empty.
	# It means that the post should also contain any of the 'perhaps'.
	# Pro tip: 'yes' yields good results
	'additive': 'yes',

	# Only accept posts that contain at least ONE of these
	'perhaps': [
		'reptile',
		'lizard',
		'dragon',
		'dinosaur',
		'scalie',
		'snake',
		'xenomorph',
		'alien_(franchise)',
	],

	# Skip posts, that are not of the specified type.
	# It's highly recommended not to use this,
	# because it means that the entire query itself is
	# executed with this filter.

	# For instance, if you executed a query and specified 'video'
	# here - you will have to re-execute the query to get other types.

	# Just use 'Quick Sort' present in the GUI, as it doesn't
	# intorduce limits like that.

	# Applicable types:
	# 'flash'
	# 'video'
	# 'image'
	# 'animated_image'
	# None (not enclosed in quotation marks) = don't filter by type
	'of_type': None,


	# A post must contain NONE of these
	'no': [
		'gore',
		'vore',
		'overweight',

		# Pro tip: This is illegal in most countries
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

	# Then - SKIP

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


