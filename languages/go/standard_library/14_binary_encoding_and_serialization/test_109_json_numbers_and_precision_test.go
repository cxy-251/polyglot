// polyglot-covers: go.encoding-json.numbers-and-precision
package serialization_test

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestUseNumberDefersNumericRepresentationChoice(t *testing.T) {
	decoder := json.NewDecoder(strings.NewReader(`{"id":9007199254740993}`))
	decoder.UseNumber()
	var value map[string]any
	if err := decoder.Decode(&value); err != nil {
		t.Fatal(err)
	}
	number := value["id"].(json.Number)
	integer, err := number.Int64()
	if err != nil || integer != 9007199254740993 {
		t.Fatalf("默认 interface 解码使用 float64；UseNumber 可避免提前丢失整数精度: %v %v", integer, err)
	}
}
