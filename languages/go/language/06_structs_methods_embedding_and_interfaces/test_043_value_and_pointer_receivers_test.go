// polyglot-covers: go.methods.receivers-and-method-sets
package objects_test

import "testing"

type receiverCounter struct{ value int }

func (counter receiverCounter) Value() int { return counter.value }
func (counter *receiverCounter) Add(delta int) {
	counter.value += delta
}

type mutator interface {
	Mutate()
}

type methodSetValue struct{ changed bool }

func (value *methodSetValue) Mutate() { value.changed = true }

func TestPointerReceiverMutatesSharedObject(t *testing.T) {
	counter := receiverCounter{value: 1}
	counter.Add(2)
	if counter.Value() != 3 {
		t.Fatal("可寻址值调用 pointer receiver 时编译器插入取址")
	}
	copy := counter
	copy.Add(4)
	if counter.Value() != 3 || copy.Value() != 7 {
		t.Fatal("复制 struct 后，pointer receiver 只修改各自副本")
	}
}

func TestPointerMethodBelongsOnlyToPointerMethodSet(t *testing.T) {
	var implementation mutator = &methodSetValue{}
	implementation.Mutate()
	if !implementation.(*methodSetValue).changed {
		t.Fatal("*T 的 method set 包含 pointer receiver 方法")
	}
	// `methodSetValue{}` 不能赋给 mutator；可寻址调用的自动取址不会扩展 T 的 interface method set。
}
