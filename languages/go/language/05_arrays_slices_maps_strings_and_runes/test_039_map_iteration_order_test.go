// polyglot-covers: go.collections.map-iteration-order
package collections_test

import "testing"

func TestMapRangeVisitsEntriesWithoutOrderingContract(t *testing.T) {
	values := map[string]int{"a": 1, "b": 2, "c": 3}
	seen := map[string]bool{}
	total := 0
	for key, value := range values {
		seen[key] = true
		total += value
	}
	if len(seen) != 3 || total != 6 {
		t.Fatal("map range 覆盖现存条目，但遍历顺序未指定")
	}
	// 测试不能断言某次观察到的顺序；需要稳定输出时先提取并排序 key。
}
