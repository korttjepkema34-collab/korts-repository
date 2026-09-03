class_name TestConfig
extends GdUnitTestSuite


func test_config_loads_clock_values() -> void:
	var cfg: Node = auto_free(load("res://scripts/config.gd").new())
	add_child(cfg)
	cfg._ready()
	assert_int(int(cfg.value("day_seconds", 0))).is_greater(0)
	assert_int(int(cfg.value("night_seconds", 0))).is_greater(0)
	assert_int(int(cfg.value("horde_cap", 0))).is_equal(150)
