// polyglot-covers: go.strconv.numeric-parsing
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
