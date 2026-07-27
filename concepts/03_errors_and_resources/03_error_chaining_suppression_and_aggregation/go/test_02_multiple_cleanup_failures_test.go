// polyglot-family: errors_and_resources
// polyglot-concept: error_chaining_suppression_and_aggregation
// polyglot-related: languages/go/language/
// polyglot-related+: 08_errors_panic_recover_and_cleanup/test_063_cleanup_failure_and_original_error_test.go
//
// 共同问题：多个清理失败能否同时保留；遍历与匹配是否覆盖每个组成原因。
// 对照观察：errors.Join 表达多分支错误；defer 本身不会自动收集多个 Close 返回值。
package error_chaining_suppression_and_aggregation

import (
	"errors"
	"testing"
)

func TestMultipleCleanupErrorsNeedExplicitAggregation(t *testing.T) {
	operation := errors.New("operation")
	closeFirst := errors.New("close first")
	closeSecond := errors.New("close second")
	combined := errors.Join(operation, closeFirst, closeSecond)
	for _, target := range []error{operation, closeFirst, closeSecond} {
		if !errors.Is(combined, target) {
			t.Fatalf("聚合错误应保留每个 identity: %v", target)
		}
	}
}
