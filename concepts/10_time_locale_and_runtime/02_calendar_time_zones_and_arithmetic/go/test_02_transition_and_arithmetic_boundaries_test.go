// polyglot-family: time_locale_and_runtime
// polyglot-concept: calendar_time_zones_and_arithmetic
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_114_time_parsing_formatting_and_locations_test.go
//
// 共同问题：DST gap/fold 如何影响本地时间；“一天”是日历单位还是固定 24 小时。
// 对照观察：Location 的 zone database 决定 offset；跨 DST 的 AddDate(一天) 可能是 23 或 25 小时。
package calendar_time_zones_and_arithmetic

import (
	"testing"
	"time"
)

func TestDSTTransitionSeparatesCalendarDayFromDuration(t *testing.T) {
	location, err := time.LoadLocation("America/New_York")
	if err != nil {
		t.Skipf("ohdev 缺少锁定时区数据: %v", err)
	}
	before := time.Date(2026, time.March, 7, 12, 0, 0, 0, location)
	nextDay := before.AddDate(0, 0, 1)
	after24Hours := before.Add(24 * time.Hour)
	if nextDay.Sub(before) != 23*time.Hour || nextDay.Hour() != 12 || after24Hours.Hour() != 13 {
		t.Fatalf("spring-forward 使本地日历日只有 23 小时: %v %v", nextDay, after24Hours)
	}
}
