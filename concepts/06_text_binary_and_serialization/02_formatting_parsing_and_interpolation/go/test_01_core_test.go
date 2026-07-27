// polyglot-family: text_binary_and_serialization
// polyglot-concept: formatting_parsing_and_interpolation
// polyglot-related: languages/go/standard_library/
// polyglot-related+: 13_text_formatting_parsing_and_regex/test_097_fmt_verbs_width_and_indexing_test.go
//
// 共同问题：值如何嵌入文本并按类型解析回来；格式错误和范围错误如何报告。
// 对照观察：Go 没有字符串插值语法；fmt 负责展示，strconv 提供显式、带 error 的基本类型解析。
package formatting_parsing_and_interpolation

import (
	"errors"
	"fmt"
	"strconv"
	"testing"
)

func TestFormattingAndParsingUseDifferentAPIs(t *testing.T) {
	formatted := fmt.Sprintf("id=%04d enabled=%t", 7, true)
	if formatted != "id=0007 enabled=true" {
		t.Fatalf("fmt verb 控制布局: %q", formatted)
	}
	_, err := strconv.ParseInt("128", 10, 8)
	var numberError *strconv.NumError
	if !errors.As(err, &numberError) || !errors.Is(numberError.Err, strconv.ErrRange) {
		t.Fatalf("strconv 保留输入、函数与具体失败原因: %v", err)
	}
	if value, err := strconv.ParseInt("0xff", 0, 64); err != nil || value != 255 {
		t.Fatalf("base=0 明确启用 Go 风格前缀识别: %d %v", value, err)
	}
}
