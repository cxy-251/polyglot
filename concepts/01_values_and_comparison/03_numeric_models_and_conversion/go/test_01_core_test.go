// polyglot-family: values_and_comparison
// polyglot-concept: numeric_models_and_conversion
// polyglot-related: languages/go/language/
// polyglot-related+: 02_declarations_types_constants_and_zero_values/test_012_numeric_conversions_and_overflow_test.go
//
// 共同问题：整数、浮点和转换采用什么表示；精度、截断与溢出何时发生。
// 对照观察：Go 数值类型固定且转换显式；常量在编译期检查，机器整数运行时按位宽运算。
package numeric_models_and_conversion

import (
	"math"
	"strconv"
	"testing"
)

func TestConversionsExposeTruncationAndWidth(t *testing.T) {
	fraction := 3.9
	wide := uint16(258)
	if int(fraction) != 3 || uint8(wide) != 2 {
		t.Fatal("浮点转整数截向零；窄化整数转换保留目标位宽")
	}
	if strconv.IntSize != 32 && strconv.IntSize != 64 {
		t.Fatalf("int 宽度由目标架构决定: %d", strconv.IntSize)
	}
	if float64(uint64(1<<53)+1) == float64(uint64(1<<53)) {
		t.Log("float64 无法精确表示 2^53 以上的每个整数，这是预期边界")
	} else {
		t.Fatal("锁定实现应遵循 IEEE 754 binary64 精度边界")
	}
	if math.IsNaN(math.Sqrt(-1)) != true {
		t.Fatal("浮点域错误可产生 NaN，而非语言异常")
	}
}
