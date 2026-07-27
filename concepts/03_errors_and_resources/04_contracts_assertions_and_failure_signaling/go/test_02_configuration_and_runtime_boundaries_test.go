// polyglot-family: errors_and_resources
// polyglot-concept: contracts_assertions_and_failure_signaling
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 13_text_formatting_parsing_and_regex/test_099_strconv_numeric_parsing_test.go
//
// 共同问题：配置文本何时验证；运行期能力缺失如何与程序错误区分。
// 对照观察：Go 解析函数返回带上下文的 error；测试应隔离环境，并在边界立即校验。
package contracts_assertions_and_failure_signaling

import (
	"os"
	"strconv"
	"testing"
)

func TestConfigurationIsValidatedAtTheBoundary(t *testing.T) {
	t.Setenv("POLYGLOT_LIMIT", "not-a-number")
	_, err := strconv.Atoi(os.Getenv("POLYGLOT_LIMIT"))
	if err == nil {
		t.Fatal("无效外部配置应在进入核心逻辑前转成显式错误")
	}
	t.Setenv("POLYGLOT_LIMIT", "8")
	value, err := strconv.Atoi(os.Getenv("POLYGLOT_LIMIT"))
	if err != nil || value != 8 {
		t.Fatalf("有效配置转换为强类型值: %d %v", value, err)
	}
}
