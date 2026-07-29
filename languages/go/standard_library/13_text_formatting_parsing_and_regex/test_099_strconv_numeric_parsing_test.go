// polyglot-covers: go.strconv.numeric-parsing-and-go-literals
package textprocessing_test

import (
	"errors"
	"strconv"
	"testing"
)

func TestNumericParsingReportsSyntaxAndRangeSeparately(t *testing.T) {
	value, err := strconv.ParseInt("7f", 16, 8)
	if err != nil || value != 127 {
		t.Fatalf("bitSize 限制结果范围: %d %v", value, err)
	}
	_, err = strconv.ParseInt("128", 10, 8)
	var numberError *strconv.NumError
	if !errors.As(err, &numberError) || !errors.Is(numberError.Err, strconv.ErrRange) {
		t.Fatalf("超范围保留 NumError 上下文: %v", err)
	}
}

func TestQuoteProducesValidGoStringLiteral(t *testing.T) {
	source := "line\n界"
	quoted := strconv.Quote(source)
	roundTrip, err := strconv.Unquote(quoted)
	if err != nil || roundTrip != source {
		t.Fatalf("Quote/Unquote 处理 Go literal 转义，不是 JSON 或 shell quoting: %q %v", quoted, err)
	}
	if strconv.QuoteToASCII("界") != `"\u754c"` {
		t.Fatal("QuoteToASCII 将非 ASCII rune 写成 Unicode escape")
	}
}
