// polyglot-covers: go.declarations.inference-and-blank-identifier
package declarations_test

import (
	"reflect"
	"strconv"
	"testing"
)

func TestInferenceUsesInitializerAndBlankDiscardsAValue(t *testing.T) {
	number := 1
	fraction := 1.5
	parsed, _ := strconv.Atoi("42")
	if reflect.TypeOf(number).Kind() != reflect.Int ||
		reflect.TypeOf(fraction).Kind() != reflect.Float64 ||
		parsed != 42 {
		t.Fatal("默认类型来自未类型化常量；blank identifier 显式丢弃不需要的结果")
	}
	// `_` 从不建立可读取绑定，也不表示可稍后恢复的占位值。
}
