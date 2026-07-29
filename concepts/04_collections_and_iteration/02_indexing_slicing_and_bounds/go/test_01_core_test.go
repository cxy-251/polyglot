// polyglot-family: collections_and_iteration
// polyglot-concept: indexing_slicing_and_bounds
// polyglot-related: languages/go/language/
// polyglot-related+: 05_arrays_slices_maps_strings_and_runes/test_035_append_reallocation_test.go
//
// 共同问题：索引单位是什么；slice 边界是否包含终点；越界与负索引如何失败。
// 对照观察：Go slice 使用半开区间并在运行时检查；string 索引返回 byte，负索引没有特殊含义。
package indexing_slicing_and_bounds

import "testing"

func TestSlicesAreHalfOpenViewsAndBoundsPanic(t *testing.T) {
	values := []int{1, 2, 3}
	view := values[1:3]
	view[0] = 20
	if len(view) != 2 || values[1] != 20 {
		t.Fatal("slice [low:high] 不含 high，并与原 slice 共享 backing array")
	}
	defer func() {
		if recover() == nil {
			t.Fatal("运行时索引越界应 panic")
		}
	}()
	_ = values[len(values)]
}

func TestStringIndexReturnsByte(t *testing.T) {
	text := "界"
	if len(text) != 3 || text[0] != 0xe7 {
		t.Fatal("string 索引单位是 byte，不是 rune 或 grapheme")
	}
}
