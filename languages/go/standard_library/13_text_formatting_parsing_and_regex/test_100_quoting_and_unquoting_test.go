// polyglot-covers: go.strconv.quoting-and-unquoting
package textprocessing_test

import (
	"strconv"
	"testing"
)

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
