// polyglot-covers: go.interfaces.any-comparable-dynamic-comparison
package objects_test

import "testing"

func TestAnyCanHoldUncomparableDynamicValue(t *testing.T) {
	var left any = []int{1}
	var right any = []int{1}
	defer func() {
		if recover() == nil {
			t.Fatal("interface 比较在动态值不可比较时 panic")
		}
	}()
	_ = left == right
}

func mapWithComparableKey[K comparable, V any](key K, value V) map[K]V {
	return map[K]V{key: value}
}
