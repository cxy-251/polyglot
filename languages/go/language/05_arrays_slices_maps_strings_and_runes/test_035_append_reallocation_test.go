// polyglot-covers: go.collections.append-reallocation
package collections_test

import "testing"

func TestAppendMayReuseOrReplaceBackingStorage(t *testing.T) {
	base := make([]int, 1, 2)
	base[0] = 1
	shared := append(base, 2)
	shared[0] = 10
	if base[0] != 10 {
		t.Fatal("容量足够时 append 可复用 backing array")
	}
	detached := append(shared, 3)
	detached[0] = 99
	if shared[0] != 10 {
		t.Fatal("容量不足时 append 分配新数组；调用方必须接收返回的 slice")
	}
}
