// polyglot-family: values_and_comparison
// polyglot-concept: ordering_hashing_and_key_semantics
// polyglot-related: languages/go/language/
// polyglot-related+: 02_declarations_types_constants_and_zero_values/test_015_comparability_test.go
//
// 共同问题：排序依据什么顺序；哈希键需要哪些契约；特殊数值会怎样破坏查找直觉。
// 对照观察：Go 只为部分内建类型定义顺序；map key 必须 comparable，用户不能覆写 hash/equality。
package ordering_hashing_and_key_semantics

import (
	"math"
	"slices"
	"testing"
)

func TestOrderingAndMapKeysUseLanguageDefinedOperations(t *testing.T) {
	values := []string{"b", "ä", "a"}
	slices.Sort(values)
	if !slices.Equal(values, []string{"a", "b", "ä"}) {
		t.Fatalf("string 排序按 UTF-8 bytes 的字典序，不按 locale collation: %v", values)
	}
	key := [2]int{1, 2}
	mapping := map[[2]int]string{key: "pair"}
	if mapping[key] != "pair" {
		t.Fatal("comparable array 可作为 map key")
	}
	nan := math.NaN()
	nanMap := map[float64]string{nan: "lost"}
	if _, found := nanMap[nan]; found {
		t.Fatal("NaN != NaN，因此即使允许作为 key，也无法用同一 NaN 值重新命中")
	}
}
