// polyglot-covers: go.generics.zero-value-and-type-switch
package generics_test

import "testing"

func zeroAndDynamicKind[T any](value T) (T, string) {
	var zero T
	switch any(value).(type) {
	case int:
		return zero, "int"
	default:
		return zero, "other"
	}
}

func TestGenericCodeBuildsZeroValueWithoutKnowingConcreteType(t *testing.T) {
	zero, kind := zeroAndDynamicKind(7)
	if zero != 0 || kind != "int" {
		t.Fatal("var zero T 产生实例化类型零值；动态检查需先装箱到 interface")
	}
}
