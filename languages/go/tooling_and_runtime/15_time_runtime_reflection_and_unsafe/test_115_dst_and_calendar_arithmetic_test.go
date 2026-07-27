// polyglot-covers: go.time.dst-and-calendar-arithmetic
package runtimeintrospection_test

import (
	"testing"
	"time"
)

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
