# gdUnit4 smoke test. Proves the headless test runner works once the addon is installed.
class_name TestSmoke
extends GdUnitTestSuite


func test_main_scene_loads() -> void:
	var packed: PackedScene = load("res://scenes/main/main.tscn")
	assert_that(packed).is_not_null()
	var inst: Node = packed.instantiate()
	assert_that(inst).is_not_null()
	inst.free()
