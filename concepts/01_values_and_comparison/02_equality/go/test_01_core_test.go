// polyglot-family: values_and_comparison
// polyglot-concept: equality
// polyglot-related: languages/go/language/
// polyglot-related+: 02_declarations_types_constants_and_zero_values/test_015_comparability_test.go
//
// 共同问题：相等比较是值、身份还是转换后的结果；哪些值不能安全比较。
// 对照观察：Go 不做跨数值类型强制转换；comparability 由完整静态类型和 interface 动态值共同决定。
package equality

import (
	"math"
	"testing"
)

type equalityRecord struct {
	code int
	name string
}

func TestComparableValuesUseStructuralEquality(t *testing.T) {
	if [2]int{1, 2} != [2]int{1, 2} ||
		(equalityRecord{code: 1, name: "go"}) != (equalityRecord{code: 1, name: "go"}) {
		t.Fatal("array 与字段全部 comparable 的 struct 按组成值比较")
	}
	if math.NaN() == math.NaN() {
		t.Fatal("IEEE NaN 不等于自身")
	}
}

func TestInterfaceComparisonChecksDynamicComparability(t *testing.T) {
	var left any = []int{1}
	var right any = []int{1}
	defer func() {
		if recover() == nil {
			t.Fatal("动态 slice 不可比较，interface == 会 panic")
		}
	}()
	_ = left == right
}
