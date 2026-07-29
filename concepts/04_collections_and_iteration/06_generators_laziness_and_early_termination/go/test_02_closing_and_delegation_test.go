// polyglot-family: collections_and_iteration
// polyglot-concept: generators_laziness_and_early_termination
// polyglot-related: languages/go/language/07_generics/test_054_generic_method_boundaries_test.go
//
// 共同问题：拉取式迭代怎样停止后台生产；一个生成器如何组合或委托给另一个。
// 对照观察：iter.Pull 返回显式 stop，调用方应 defer；组合 Seq 需逐项转发 yield 的停止信号。
package generators_laziness_and_early_termination

import (
	"iter"
	"testing"
)

func concatenate(first, second iter.Seq[int]) iter.Seq[int] {
	return func(yield func(int) bool) {
		for value := range first {
			if !yield(value) {
				return
			}
		}
		for value := range second {
			if !yield(value) {
				return
			}
		}
	}
}

func TestPullHasExplicitStopAndCompositionForwardsValues(t *testing.T) {
	sequence := concatenate(func(yield func(int) bool) { yield(1) }, func(yield func(int) bool) { yield(2) })
	next, stop := iter.Pull(sequence)
	defer stop()
	first, ok := next()
	second, secondOK := next()
	if first != 1 || !ok || second != 2 || !secondOK {
		t.Fatal("Pull 将 push sequence 适配为 next/stop；组合保持顺序")
	}
}
