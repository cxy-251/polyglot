// polyglot-covers: go.declarations.var-const-short
package declarations_test

import "testing"

func TestDeclarationsChooseStorageAndInference(t *testing.T) {
	var explicit int = 3
	inferred := 4
	const compileTime = 5
	if explicit+inferred+compileTime != 12 {
		t.Fatal("var、短声明与 const 均可参与表达式")
	}
	// `:=` 至少要在当前作用域引入一个新变量，且只能用于函数体。
}
