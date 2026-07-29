// polyglot-covers: go.packages.initialization-order-and-blank-import
package packagesmodules_test

import (
	"go/parser"
	"go/token"
	"slices"
	"testing"

	"polyglot.local/go-course/tooling_and_runtime/09_packages_modules_imports_and_initialization/initfixture"
)

var initializationEvents = []string{"variable"}

func init() {
	initializationEvents = append(initializationEvents, "init")
}

func ordinaryFunction() string { return "callable" }

func TestImportedPackageInitializesBeforeImporterTests(t *testing.T) {
	if !slices.Equal(initfixture.Events, []string{"variable", "init"}) {
		t.Fatalf("依赖 package 先初始化变量再运行 init: %v", initfixture.Events)
	}
	source := `package p; import _ "image/png"`
	if _, err := parser.ParseFile(token.NewFileSet(), "blank.go", source, parser.ImportsOnly); err != nil {
		t.Fatal(err)
	}
	// blank import 没有本地名称，只为被导入 package 的初始化副作用；应谨慎记录这种隐式注册。
}

func TestCurrentPackageInitializesVariablesBeforeInitFunctions(t *testing.T) {
	if !slices.Equal(initializationEvents, []string{"variable", "init"}) {
		t.Fatalf("package 变量先初始化，随后按文件顺序运行 init: %v", initializationEvents)
	}
	if ordinaryFunction() != "callable" {
		t.Fatal("普通函数由调用触发；init 不能被普通表达式调用")
	}
}
