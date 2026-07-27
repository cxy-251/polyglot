// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_114_time_parsing_formatting_and_locations_test.go
//
// 共同问题：区域数据缺失如何失败；进程级 locale/zone 状态是否会隐式改变 API。
// 对照观察：LoadLocation 显式返回 error；标准库没有通用 locale object，国际化需选择额外实现。
package locale_numbers_dates_and_collation

import (
	"testing"
	"time"
)

func TestZoneAvailabilityIsAnExplicitRuntimeCapability(t *testing.T) {
	if _, err := time.LoadLocation("Invalid/Polyglot_Zone"); err == nil {
		t.Fatal("未知 zone name 返回 error，而非静默回退到本地时区")
	}
	fixed := time.FixedZone("explicit", 90*60)
	_, offset := time.Date(2026, 1, 1, 0, 0, 0, 0, fixed).Zone()
	if offset != 90*60 {
		t.Fatal("FixedZone 不依赖外部 tzdata，但只表达固定 offset")
	}
}
