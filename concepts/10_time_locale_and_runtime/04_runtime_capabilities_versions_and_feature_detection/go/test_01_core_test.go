// polyglot-family: time_locale_and_runtime
// polyglot-concept: runtime_capabilities_versions_and_feature_detection
// polyglot-related: languages/go/language/
// polyglot-related+: 06_structs_methods_embedding_and_interfaces/test_045_implicit_interface_satisfaction_test.go
//
// 共同问题：如何识别语言/运行时版本、平台和可用能力；版本字符串能否替代能力检查。
// 对照观察：runtime 暴露锁定版本和目标平台；行为分支优先使用 interface、build tag 或实际 API 检查。
package runtime_capabilities_versions_and_feature_detection

import (
	"io"
	"runtime"
	"strings"
	"testing"
)

type stringCapability struct{}

func (stringCapability) String() string { return "available" }

func TestVersionPlatformAndInterfaceCapabilityAreSeparate(t *testing.T) {
	if runtime.GOOS == "" || runtime.GOARCH == "" {
		t.Fatalf("目标平台是当前二进制的实现观察: %s/%s", runtime.GOOS, runtime.GOARCH)
	}
	var value any = stringCapability{}
	if capability, ok := value.(interface{ String() string }); !ok || capability.String() != "available" {
		t.Fatal("行为能力优先通过所需最小 interface 检查")
	}
	var reader io.Reader = strings.NewReader("go")
	if reader == nil {
		t.Fatal("编译期 interface satisfaction 比版本号分支更精确")
	}
	// runtime.Version 可用于诊断，但版本字符串不能替代最小 interface 或实际操作的能力检查。
}
