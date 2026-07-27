// polyglot-family: objects_and_dispatch
// polyglot-concept: encapsulation_private_state_and_immutability
// polyglot-related: languages/go/language/
// polyglot-related+: 06_structs_methods_embedding_and_interfaces/test_043_value_and_pointer_receivers_test.go
//
// 共同问题：私有状态边界在哪里；只读或不可变值如何表达；复制是否泄露内部别名。
// 对照观察：Go 可见性由 package 与首字母大小写决定；不可变通常通过未导出字段和返回副本约定实现。
package encapsulation_private_state_and_immutability

import "testing"

type immutableNames struct{ values []string }

func newImmutableNames(values []string) immutableNames {
	return immutableNames{values: append([]string(nil), values...)}
}

func (names immutableNames) Values() []string {
	return append([]string(nil), names.values...)
}

func TestDefensiveCopiesProtectSliceBackedState(t *testing.T) {
	input := []string{"go"}
	value := newImmutableNames(input)
	input[0] = "changed"
	output := value.Values()
	output[0] = "also changed"
	if value.Values()[0] != "go" {
		t.Fatal("未导出字段不够；slice 输入和输出都需复制才能维持不可变契约")
	}
}
