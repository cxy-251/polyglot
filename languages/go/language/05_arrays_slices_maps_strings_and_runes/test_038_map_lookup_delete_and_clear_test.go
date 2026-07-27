// polyglot-covers: go.collections.map-lookup-delete-clear
package collections_test

import "testing"

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
