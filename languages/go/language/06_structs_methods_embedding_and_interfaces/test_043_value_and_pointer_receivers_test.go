// polyglot-covers: go.methods.value-and-pointer-receivers
package objects_test

import "testing"

type receiverCounter struct{ value int }

func (counter receiverCounter) Value() int { return counter.value }
func (counter *receiverCounter) Add(delta int) {
	counter.value += delta
}

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
