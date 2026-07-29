// polyglot-covers: go.declarations.bindings-and-inference
package declarations_test

import (
	"reflect"
	"strconv"
	"testing"
)

func TestDeclarationsChooseStorageAndInference(t *testing.T) {
	var explicit int = 3
	inferred := 4
	const compileTime = 5
	if explicit+inferred+compileTime != 12 {
		t.Fatal("var、短声明与 const 均可参与表达式")
	}
	// `:=` 至少要在当前作用域引入一个新变量，且只能用于函数体。
}

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
