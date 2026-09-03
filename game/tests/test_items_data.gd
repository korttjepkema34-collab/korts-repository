class_name TestItemsData
extends GdUnitTestSuite


func _load(path: String) -> Array:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	assert_that(parsed).is_not_null()
	return parsed as Array


func test_generated_item_counts() -> void:
	assert_int(_load("res://data/weapons.json").size()).is_equal(25)
	assert_int(_load("res://data/armor.json").size()).is_equal(12)
	assert_int(_load("res://data/classes.json").size()).is_equal(10)
	assert_int(_load("res://data/rarities.json").size()).is_equal(5)


func test_every_class_starting_weapon_exists() -> void:
	var ids: Dictionary = {}
	for w: Dictionary in _load("res://data/weapons.json"):
		ids[w["id"]] = true
	for c: Dictionary in _load("res://data/classes.json"):
		assert_bool(ids.has(c["starting_weapon"])).override_failure_message("missing weapon for " + str(c["name"])).is_true()
