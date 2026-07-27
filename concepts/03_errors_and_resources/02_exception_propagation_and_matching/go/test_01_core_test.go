// polyglot-family: errors_and_resources
// polyglot-concept: exception_propagation_and_matching
// polyglot-related: languages/go/language/
// polyglot-related+: 08_errors_panic_recover_and_cleanup/test_058_typed_errors_and_errors_as_test.go
//
// 共同问题：失败如何跨调用传播；调用方按身份还是类型匹配；未处理失败如何终止。
// 对照观察：Go 的预期失败是显式 error 值，不存在独立 exception hierarchy；panic 用于异常控制流。
package exception_propagation_and_matching

import (
	"errors"
	"fmt"
	"testing"
)

type requestError struct{ Code int }

func (err *requestError) Error() string { return fmt.Sprintf("code %d", err.Code) }

func innerFailure() error { return &requestError{Code: 404} }
func outerFailure() error { return fmt.Errorf("load: %w", innerFailure()) }

func TestErrorPropagationAndTypedMatchingAreExplicit(t *testing.T) {
	err := outerFailure()
	var typed *requestError
	if !errors.As(err, &typed) || typed.Code != 404 {
		t.Fatal("每层显式 return/wrap error；errors.As 沿链匹配可赋值类型")
	}
}
