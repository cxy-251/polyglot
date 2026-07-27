// polyglot-covers: go.functions.value-parameters
package functions_test

import "testing"

func replaceNumber(value int) { value = 99 }
func replaceThroughPointer(value *int) {
	*value = 99
}

func TestParameterVariablesReceiveCopies(t *testing.T) {
	number := 1
	replaceNumber(number)
	if number != 1 {
		t.Fatal("普通参数复制值，重绑形参不影响调用方")
	}
	replaceThroughPointer(&number)
	if number != 99 {
		t.Fatal("指针本身也按值复制，但复制的指针仍指向同一存储")
	}
}
