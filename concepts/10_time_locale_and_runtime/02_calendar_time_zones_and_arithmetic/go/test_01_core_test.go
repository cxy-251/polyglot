// polyglot-family: time_locale_and_runtime
// polyglot-concept: calendar_time_zones_and_arithmetic
// polyglot-related: languages/go/tooling_and_runtime/
// polyglot-related+: 15_time_runtime_reflection_and_unsafe/test_114_time_parsing_formatting_and_locations_test.go
//
// 共同问题：日期时间怎样携带 zone；calendar 加法与固定 duration 加法是否相同。
// 对照观察：Go Time 保存 location 规则引用；AddDate 按日历字段归一化，Add 按时间线 duration。
package calendar_time_zones_and_arithmetic

import (
	"testing"
	"time"
)

func TestCalendarConstructionAndTimelineAdditionAreExplicit(t *testing.T) {
	location := time.FixedZone("course", 8*60*60)
	value := time.Date(2026, time.July, 27, 9, 0, 0, 0, location)
	if value.UTC().Hour() != 1 || value.Location() != location {
		t.Fatal("Time 表示 instant 并携带用于显示本地字段的 Location")
	}
	if value.AddDate(0, 0, 1).Day() != 28 || value.Add(24*time.Hour).Sub(value) != 24*time.Hour {
		t.Fatal("AddDate 表达 calendar 意图；Add 表达时间线长度")
	}
}
