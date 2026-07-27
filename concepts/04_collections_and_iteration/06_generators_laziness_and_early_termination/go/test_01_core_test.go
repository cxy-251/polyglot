// polyglot-family: collections_and_iteration
// polyglot-concept: generators_laziness_and_early_termination
// polyglot-related: languages/go/language/07_generics/test_056_generic_algorithms_and_containers_test.go
//
// 共同问题：序列何时开始生产；提前停止是否通知生产者；状态能否重复迭代。
// 对照观察：iter.Seq 是接受 yield callback 的函数；调用或 range 时才执行，yield false 表示停止。
package generators_laziness_and_early_termination

import (
	"iter"
	"testing"
)

func observedSequence(events *[]int) iter.Seq[int] {
	return func(yield func(int) bool) {
		for value := range 5 {
			*events = append(*events, value)
			if !yield(value) {
				return
			}
		}
	}
}

func TestSequenceIsLazyAndHonorsEarlyTermination(t *testing.T) {
	events := []int{}
	sequence := observedSequence(&events)
	if len(events) != 0 {
		t.Fatal("构造 Seq 不执行生产逻辑")
	}
	for value := range sequence {
		if value == 1 {
			break
		}
	}
	if len(events) != 2 {
		t.Fatalf("break 通过 yield=false 阻止继续生产: %v", events)
	}
}
