// polyglot-family: collections_and_iteration
// polyglot-concept: sequence_mutation_and_invalidation
// polyglot-related: languages/go/language/
// polyglot-related+: 05_arrays_slices_maps_strings_and_runes/test_035_append_reallocation_test.go
//
// 共同问题：结构修改后旧引用或 iterator 是否仍有效；扩容何时断开共享关系。
// 对照观察：Go slice 没有 iterator 对象；append 可能更换 backing array，因此必须使用返回值。
package sequence_mutation_and_invalidation

import "testing"

func TestAppendMayDetachOneSliceFromAnother(t *testing.T) {
	base := []int{1, 2}
	alias := base
	grown := append(base, 3)
	grown[0] = 9
	if alias[0] != 1 {
		t.Fatal("容量不足时 grown 指向新数组，旧 slice 仍有效但不再观察新写入")
	}
	if len(alias) != 2 || len(grown) != 3 {
		t.Fatal("每个 slice header 独立保存长度")
	}
}
