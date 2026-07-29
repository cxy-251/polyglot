// polyglot-covers: go.time.locations-layouts-dst-and-calendar-arithmetic
package runtimeintrospection_test

import (
	"testing"
	"time"
)

func TestLayoutsUseReferenceTimeAndLocationIsExplicit(t *testing.T) {
	const layout = "2006-01-02 15:04 MST"
	value, err := time.Parse(layout, "2026-07-27 08:30 UTC")
	if err != nil {
		t.Fatal(err)
	}
	if value.Location() != time.UTC || value.Format(time.RFC3339) != "2026-07-27T08:30:00Z" {
		t.Fatalf("layout 用固定参考时间描述字段；Parse 结果携带 location: %v", value)
	}
}

func TestAddDateUsesCalendarWhileAddUsesTimelineDuration(t *testing.T) {
	location, err := time.LoadLocation("America/New_York")
	if err != nil {
		t.Skipf("ohdev 缺少锁定时区数据: %v", err)
	}
	before := time.Date(2026, time.March, 7, 12, 0, 0, 0, location)
	calendarNext := before.AddDate(0, 0, 1)
	timelineNext := before.Add(24 * time.Hour)
	if calendarNext.Hour() != 12 || timelineNext.Hour() != 13 ||
		calendarNext.Sub(before) != 23*time.Hour {
		t.Fatalf("DST 跳变使本地一天与 24 小时时长不等价: %v %v", calendarNext, timelineNext)
	}
}
