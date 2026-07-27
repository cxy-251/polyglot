// polyglot-family: collections_and_iteration
// polyglot-concept: sets_membership_and_deduplication
// polyglot-related: languages/go/language/07_generics/test_052_comparable_constraints_test.go
//
// 共同问题：集合如何表示、判定成员和去重；元素必须满足什么 equality/hash 契约。
// 对照观察：Go 标准库没有通用 Set 类型，常用 map[T]struct{}；T 必须 comparable。
package sets_membership_and_deduplication

import "testing"

func makeSet[T comparable](values ...T) map[T]struct{} {
	result := make(map[T]struct{}, len(values))
	for _, value := range values {
		result[value] = struct{}{}
	}
	return result
}

func TestMapBackedSetDeduplicatesComparableValues(t *testing.T) {
	set := makeSet("go", "go", "cpp")
	_, containsGo := set["go"]
	if len(set) != 2 || !containsGo {
		t.Fatal("重复 map key 覆盖同一条目；零大小 struct 不携带业务值")
	}
	delete(set, "go")
	if _, found := set["go"]; found {
		t.Fatal("delete 实现集合移除")
	}
}
