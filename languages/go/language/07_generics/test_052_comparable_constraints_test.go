// polyglot-covers: go.generics.comparable-zero-values-and-dynamic-boundaries
package generics_test

import "testing"

func containsKey[K comparable, V any](values map[K]V, key K) bool {
	_, ok := values[key]
	return ok
}

func zeroAndDynamicKind[T any](value T) (T, string) {
	var zero T
	switch any(value).(type) {
	case int:
		return zero, "int"
	default:
		return zero, "other"
	}
}

func TestComparableConstraintEnablesEqualityAndMapKeys(t *testing.T) {
	if !containsKey(map[[2]int]string{{1, 2}: "pair"}, [2]int{1, 2}) {
		t.Fatal("comparable 允许 ==、!= 和 map key；array 的元素也必须可比较")
	}
	// slice 不满足 comparable，因此会在实例化处被编译器拒绝。
}

func TestGenericCodeBuildsZeroValueWithoutKnowingConcreteType(t *testing.T) {
	zero, kind := zeroAndDynamicKind(7)
	if zero != 0 || kind != "int" {
		t.Fatal("var zero T 产生实例化类型零值；动态检查需先装箱到 interface")
	}
}
