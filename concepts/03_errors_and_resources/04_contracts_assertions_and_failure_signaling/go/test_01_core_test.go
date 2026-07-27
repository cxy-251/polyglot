// polyglot-family: errors_and_resources
// polyglot-concept: contracts_assertions_and_failure_signaling
// polyglot-related: languages/go/language/
// polyglot-related+: 08_errors_panic_recover_and_cleanup/test_057_error_values_and_sentinels_test.go
//
// 共同问题：调用前置条件、可恢复失败与不变量破坏分别如何表达。
// 对照观察：Go 常用类型系统和显式 error 表达 API contract；panic 不应代替普通输入校验。
package contracts_assertions_and_failure_signaling

import (
	"errors"
	"testing"
)

var contractRangeError = errors.New("value must be positive")

func requirePositive(value int) error {
	if value <= 0 {
		return contractRangeError
	}
	return nil
}

func TestRecoverableContractViolationReturnsError(t *testing.T) {
	if !errors.Is(requirePositive(0), contractRangeError) || requirePositive(1) != nil {
		t.Fatal("调用方可处理的边界使用 error，而非依赖禁用/启用的 assertion")
	}
}
