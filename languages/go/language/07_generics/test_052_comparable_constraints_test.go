// polyglot-covers: go.generics.comparable
package generics_test

import "testing"

func containsKey[K comparable, V any](values map[K]V, key K) bool {
	_, ok := values[key]
	return ok
}

func TestComparableConstraintEnablesEqualityAndMapKeys(t *testing.T) {
	if !containsKey(map[[2]int]string{{1, 2}: "pair"}, [2]int{1, 2}) {
		t.Fatal("comparable 允许 ==、!= 和 map key；array 的元素也必须可比较")
	}
	// slice 不满足 comparable，因此会在实例化处被编译器拒绝。
}
