// polyglot-covers: go.methods.method-sets
package objects_test

import "testing"

type mutator interface {
	Mutate()
}

type methodSetValue struct{ changed bool }

func (value *methodSetValue) Mutate() { value.changed = true }

func TestPointerMethodBelongsOnlyToPointerMethodSet(t *testing.T) {
	var implementation mutator = &methodSetValue{}
	implementation.Mutate()
	if !implementation.(*methodSetValue).changed {
		t.Fatal("*T 的 method set 包含 pointer receiver 方法")
	}
	// `methodSetValue{}` 不能赋给 mutator；可寻址调用的自动取址不会扩展 T 的 interface method set。
}
