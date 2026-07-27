// polyglot-family: errors_and_resources
// polyglot-concept: error_chaining_suppression_and_aggregation
// polyglot-related: languages/go/language/
// polyglot-related+: 08_errors_panic_recover_and_cleanup/test_059_wrapping_is_and_join_test.go
//
// 共同问题：如何保留失败上下文、隐藏或暴露原因、表达多个同时成立的错误。
// 对照观察：Go 用 `%w`、Unwrap、Is/As 和 Join 构造显式错误图，没有隐式 exception context。
package error_chaining_suppression_and_aggregation

import (
	"errors"
	"fmt"
	"testing"
)

func TestWrappingAndJoiningPreserveMachineReadableCauses(t *testing.T) {
	first := errors.New("first")
	second := errors.New("second")
	err := errors.Join(fmt.Errorf("context: %w", first), second)
	if !errors.Is(err, first) || !errors.Is(err, second) {
		t.Fatal("格式化文本不负责匹配；%w 和 Join 保留 unwrap 关系")
	}
	opaque := fmt.Errorf("public message: %v", first)
	if errors.Is(opaque, first) {
		t.Fatal("普通格式化 verb 只复制文本，可有意不暴露底层错误身份")
	}
}
