// polyglot-family: values_and_comparison
// polyglot-concept: identity_aliasing_and_copying
// polyglot-related: languages/go/language/
// polyglot-related+: 05_arrays_slices_maps_strings_and_runes/test_034_slice_header_length_and_capacity_test.go
//
// 共同问题：赋值复制什么；哪些值仍共享底层状态；身份如何显式观察。
// 对照观察：Go 一切赋值都复制值，但 pointer、slice、map 等复制后的描述符仍可指向共享状态。
package identity_aliasing_and_copying

import "testing"

func TestValueCopyAndAliasingAreSeparateQuestions(t *testing.T) {
	array := [2]int{1, 2}
	arrayCopy := array
	arrayCopy[0] = 9
	if array[0] != 1 {
		t.Fatal("array 赋值复制元素")
	}
	slice := []int{1, 2}
	sliceCopy := slice
	sliceCopy[0] = 9
	if slice[0] != 9 || &slice[0] != &sliceCopy[0] {
		t.Fatal("slice header 被复制，但两个 header 可指向同一 backing array")
	}
	mapping := map[string]int{"value": 1}
	mappingCopy := mapping
	mappingCopy["value"] = 9
	if mapping["value"] != 9 {
		t.Fatal("map 值复制后仍引用同一运行时映射")
	}
}
