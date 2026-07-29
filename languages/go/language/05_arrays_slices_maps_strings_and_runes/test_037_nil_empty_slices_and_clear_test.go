// polyglot-covers: go.collections.nil-slices-map-lookup-and-clear
package collections_test

import "testing"

func TestNilAndEmptySlicesShareLengthButNotNilState(t *testing.T) {
	var absent []int
	empty := []int{}
	if len(absent) != 0 || len(empty) != 0 || absent != nil || empty == nil {
		t.Fatal("nil slice 与非 nil empty slice 的长度都为零，但 nil 状态不同")
	}
	values := []int{1, 2}
	clear(values)
	if values[0] != 0 || len(values) != 2 {
		t.Fatal("clear 将元素设为零值，不改变 slice 长度")
	}
}

func TestMapLookupSeparatesMissingFromStoredZero(t *testing.T) {
	counts := map[string]int{"present": 0, "other": 2}
	value, ok := counts["present"]
	missing, found := counts["missing"]
	if value != 0 || !ok || missing != 0 || found {
		t.Fatal("单值查询返回零值；comma-ok 才区分缺失键与存储的零值")
	}
	delete(counts, "missing")
	clear(counts)
	if len(counts) != 0 {
		t.Fatal("删除缺失键安全；clear 移除全部条目")
	}
}
