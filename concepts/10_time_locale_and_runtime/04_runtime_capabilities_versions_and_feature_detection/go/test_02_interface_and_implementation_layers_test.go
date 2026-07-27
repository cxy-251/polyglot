// polyglot-family: time_locale_and_runtime
// polyglot-concept: runtime_capabilities_versions_and_feature_detection
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 09_packages_modules_imports_and_initialization/test_071_build_tags_and_platform_files_test.go
//
// 共同问题：规范接口、构建配置和当前实现观察如何分层；平台特性缺失怎样表达。
// 对照观察：build constraints 在编译前选择文件；runtime 观察当前二进制，不能证明所有目标都支持同一能力。
package runtime_capabilities_versions_and_feature_detection

import (
	"go/build"
	"runtime"
	"testing"
)

func TestBuildAndRuntimeLayersReportDifferentFacts(t *testing.T) {
	context := build.Default
	if context.GOOS != runtime.GOOS || context.GOARCH != runtime.GOARCH {
		t.Fatalf("默认 build context 应描述当前工具链目标: %s/%s %s/%s",
			context.GOOS, context.GOARCH, runtime.GOOS, runtime.GOARCH)
	}
	if context.CgoEnabled {
		t.Log("当前锁定构建环境启用 cgo；这是实现能力，不是 Go 语言保证")
	} else {
		t.Log("当前锁定构建环境禁用 cgo；纯 Go package 仍可工作")
	}
	// 需要平台 API 时用 build tag 提供实现和 fallback，而不是只解析 runtime.Version 字符串。
}
