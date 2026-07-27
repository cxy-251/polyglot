// polyglot-covers: go.initialization.init-functions
package functions_test

import (
	"slices"
	"testing"
)

var initializationEvents = []string{"variable"}

func init() {
	initializationEvents = append(initializationEvents, "init")
}

func ordinaryFunction() string { return "callable" }

func TestInitRunsAfterVariablesAndBeforeTests(t *testing.T) {
	if !slices.Equal(initializationEvents, []string{"variable", "init"}) {
		t.Fatalf("package 变量先初始化，随后按文件顺序运行 init: %v", initializationEvents)
	}
	if ordinaryFunction() != "callable" {
		t.Fatal("普通函数由调用触发；init 不能被普通表达式调用")
	}
}
