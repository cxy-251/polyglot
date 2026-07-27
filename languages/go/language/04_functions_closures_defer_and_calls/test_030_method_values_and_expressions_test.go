// polyglot-covers: go.methods.values-and-expressions
package functions_test

import "testing"

type multiplier struct{ factor int }

func (receiver multiplier) Scale(value int) int { return receiver.factor * value }

func TestMethodValueBindsReceiverWhileExpressionExposesIt(t *testing.T) {
	item := multiplier{factor: 3}
	bound := item.Scale
	unbound := multiplier.Scale
	item.factor = 9
	if bound(2) != 6 {
		t.Fatal("value receiver 的 method value 在求值时复制并绑定 receiver")
	}
	if unbound(item, 2) != 18 {
		t.Fatal("method expression 把 receiver 变成显式第一个参数")
	}
}
