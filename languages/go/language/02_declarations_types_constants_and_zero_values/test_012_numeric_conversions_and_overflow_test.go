// polyglot-covers: go.types.numeric-conversion-and-zero-values
package declarations_test

import "testing"

type zeroRecord struct {
	count int
	ready bool
	name  string
}

func TestNumericConversionsAreExplicitAndMachineValuesWrap(t *testing.T) {
	var wide int16 = 258
	narrow := uint8(wide)
	if narrow != 2 {
		t.Fatalf("窄化转换保留低位，得到 %d", narrow)
	}
	maximum := uint8(255)
	maximum++
	if maximum != 0 {
		t.Fatal("无符号整数运行时运算按 2^n 取模")
	}
	// 超出范围的常量转换会在编译期失败，不会像运行时机器整数转换那样截断。
}

func TestDeclaredStorageStartsAtRecursiveZeroValue(t *testing.T) {
	var record zeroRecord
	var numbers [2]int
	if record != (zeroRecord{}) || numbers != [2]int{0, 0} {
		t.Fatal("struct 与 array 的零值由字段和元素零值递归组成")
	}
	var pointer *zeroRecord
	if pointer != nil {
		t.Fatal("pointer 的零值是 nil")
	}
}
