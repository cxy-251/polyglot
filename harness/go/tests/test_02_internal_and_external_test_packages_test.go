// polyglot-harness: go.internal_and_external_test_packages
package goharness_test

import (
	"testing"

	course "polyglot.local/go-course/tests"
)

func TestExternalPackageUsesOnlyExportedAPI(t *testing.T) {
	if course.ExportedLabel != "course" || course.Add(4, 5) != 9 {
		t.Fatal("外部测试包应像真实使用者一样通过 import 访问导出 API")
	}
	// `internalLabel` 在这里不可见；该编译期边界防止黑盒测试依赖实现细节。
}
