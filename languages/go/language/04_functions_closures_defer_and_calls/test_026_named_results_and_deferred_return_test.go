// polyglot-covers: go.functions.named-results-and-return
package functions_test

import "testing"

func incrementOnReturn() (result int) {
	result = 4
	defer func() { result++ }()
	return
}

func TestDeferredFunctionCanObserveNamedResult(t *testing.T) {
	if incrementOnReturn() != 5 {
		t.Fatal("return 先写入命名结果，随后 defer 可在函数真正返回前修改它")
	}
	// 过度依赖命名结果的隐式修改会降低可读性，应只用于清晰的收尾语义。
}
