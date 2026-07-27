// polyglot-covers: go.numeric.conversion-and-overflow
package declarations_test

import "testing"

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
