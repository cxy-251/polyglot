// polyglot-covers: go.interfaces.assertions-switches-and-dynamic-comparison
package objects_test

import "testing"

func TestCommaOkAssertionAvoidsPanic(t *testing.T) {
	var value any = "go"
	text, ok := value.(string)
	_, integerOK := value.(int)
	if text != "go" || !ok || integerOK {
		t.Fatal("comma-ok assertion 报告动态类型是否匹配")
	}
	switch value.(type) {
	case string:
		return
	default:
		t.Fatal("type switch 应匹配 string 动态类型")
	}
}

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
