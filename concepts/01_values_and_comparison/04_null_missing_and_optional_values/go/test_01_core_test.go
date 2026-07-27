// polyglot-family: values_and_comparison
// polyglot-concept: null_missing_and_optional_values
// polyglot-related: languages/go/language/
// polyglot-related+: 02_declarations_types_constants_and_zero_values/test_014_nil_and_typed_nil_test.go
//
// 共同问题：空引用、缺失字段和可选结果如何表示；容器与 interface 的空状态是否等价。
// 对照观察：Go 的 nil 只适用于特定类型；comma-ok 和额外 bool 常用于表达“缺失”。
package null_missing_and_optional_values

import "testing"

type optionalError struct{}

func (*optionalError) Error() string { return "typed nil" }

func TestNilStateDependsOnStaticAndDynamicType(t *testing.T) {
	var pointer *optionalError
	var err error = pointer
	if pointer != nil || err == nil {
		t.Fatal("interface 包含动态类型后即使动态指针为 nil，自身也不等于 nil")
	}
	var values []int
	values = append(values, 1)
	if len(values) != 1 {
		t.Fatal("nil slice 可直接 append，零值可用")
	}
	counts := map[string]int{"zero": 0}
	_, present := counts["missing"]
	if present {
		t.Fatal("comma-ok 区分缺失键与存储的零值")
	}
}
