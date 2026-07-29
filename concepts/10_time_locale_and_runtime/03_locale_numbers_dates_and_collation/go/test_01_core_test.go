// polyglot-family: time_locale_and_runtime
// polyglot-concept: locale_numbers_dates_and_collation
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 13_text_formatting_parsing_and_regex/test_097_fmt_verbs_width_and_indexing_test.go
//
// 共同问题：数字、日期与排序是否受 locale 影响；默认 locale 来自哪里。
// 对照观察：Go fmt、strconv、time layout 和 string 比较默认不做 locale-sensitive formatting/collation。
package locale_numbers_dates_and_collation

import (
	"fmt"
	"slices"
	"testing"
	"time"
)

func TestStandardFormattingAndOrderingAreLocaleIndependent(t *testing.T) {
	if fmt.Sprintf("%.1f", 1234.5) != "1234.5" {
		t.Fatal("fmt 使用点号且不自动插入 locale 分组")
	}
	value := time.Date(2026, 7, 27, 0, 0, 0, 0, time.UTC)
	if value.Format("2006-01-02") != "2026-07-27" {
		t.Fatal("time layout 使用参考时间模式，不读取进程 locale")
	}
	names := []string{"ä", "b", "a"}
	slices.Sort(names)
	if !slices.Equal(names, []string{"a", "b", "ä"}) {
		t.Fatalf("string 顺序是 byte 字典序，不是语言学 collation: %v", names)
	}
}

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
