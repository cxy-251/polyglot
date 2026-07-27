// polyglot-family: collections_and_iteration
// polyglot-concept: iteration_protocol
// polyglot-related: languages/go/language/
// polyglot-related+: 05_arrays_slices_maps_strings_and_runes/test_040_utf8_strings_bytes_and_runes_test.go
//
// 共同问题：循环从对象取得什么；索引、元素与结束信号如何表达；迭代是否一次性。
// 对照观察：Go 的 range 由编译器支持多种内建形态；string 产生 byte index 与 rune。
package iteration_protocol

import (
	"slices"
	"testing"
)

func TestRangeShapeDependsOnOperandType(t *testing.T) {
	indexes := []int{}
	values := []rune{}
	for index, value := range "A界" {
		indexes = append(indexes, index)
		values = append(values, value)
	}
	if !slices.Equal(indexes, []int{0, 1}) || !slices.Equal(values, []rune{'A', '界'}) {
		t.Fatalf("string range 解码 UTF-8，index 仍是 byte offset: %v %v", indexes, values)
	}
	channel := make(chan int, 2)
	channel <- 1
	channel <- 2
	close(channel)
	total := 0
	for value := range channel {
		total += value
	}
	if total != 3 {
		t.Fatal("channel range 持续 receive，直到关闭且缓冲耗尽")
	}
}
