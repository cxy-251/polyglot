// polyglot-family: errors_and_resources
// polyglot-concept: resource_cleanup
// polyglot-related: languages/go/language/
// polyglot-related+: 08_errors_panic_recover_and_cleanup/test_062_partial_acquisition_test.go
//
// 共同问题：部分取得资源后失败怎样收尾；清理错误与原始错误冲突时保留什么。
// 对照观察：Go 只 defer 已成功取得的资源；清理失败不会自动聚合，必须显式组合 error。
package resource_cleanup

import (
	"errors"
	"testing"
)

var resourceOperationError = errors.New("operation")
var resourceCleanupError = errors.New("cleanup")

func acquireAndFail() (events []string, err error) {
	events = append(events, "acquire:first")
	defer func() {
		events = append(events, "release:first")
		err = errors.Join(err, resourceCleanupError)
	}()
	return events, resourceOperationError
}

func TestPartialAcquisitionPreservesBothFailures(t *testing.T) {
	events, err := acquireAndFail()
	if len(events) != 2 || !errors.Is(err, resourceOperationError) || !errors.Is(err, resourceCleanupError) {
		t.Fatalf("清理应紧随成功 acquisition 注册，并显式合并错误: %v %v", events, err)
	}
}
