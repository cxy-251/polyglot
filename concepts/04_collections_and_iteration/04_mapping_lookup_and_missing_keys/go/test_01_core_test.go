// polyglot-family: collections_and_iteration
// polyglot-concept: mapping_lookup_and_missing_keys
// polyglot-related: languages/go/language/
// polyglot-related+: 05_arrays_slices_maps_strings_and_runes/test_038_map_lookup_delete_and_clear_test.go
//
// 共同问题：查找缺失键返回什么；默认值是否写回；键类型受到什么限制。
// 对照观察：Go 单值查找返回元素零值，comma-ok 才区分缺失；查找本身不插入键。
package mapping_lookup_and_missing_keys

import "testing"

func TestCommaOkSeparatesMissingFromStoredZero(t *testing.T) {
	values := map[string]int{"zero": 0}
	stored, storedOK := values["zero"]
	missing, missingOK := values["missing"]
	if stored != 0 || !storedOK || missing != 0 || missingOK || len(values) != 1 {
		t.Fatal("缺失查找不修改 map；单值结果与存储零值相同")
	}
	var absent map[string]int
	if absent["key"] != 0 {
		t.Fatal("nil map 可读取；写入 nil map 会 panic")
	}
}
