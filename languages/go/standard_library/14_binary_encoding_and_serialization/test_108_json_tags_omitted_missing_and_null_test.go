// polyglot-covers: go.encoding-json.fields-null-and-number-precision
package serialization_test

import (
	"encoding/json"
	"strings"
	"testing"
)

type jsonRecord struct {
	Name  string  `json:"name"`
	Count int     `json:"count,omitempty"`
	Note  *string `json:"note"`
}

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

func TestJSONTagsAndPointerFieldsSeparateNullFromValue(t *testing.T) {
	encoded, err := json.Marshal(jsonRecord{Name: "go"})
	if err != nil || string(encoded) != `{"name":"go","note":null}` {
		t.Fatalf("omitempty 省略零值字段；nil pointer 编码为 null: %s %v", encoded, err)
	}
	target := jsonRecord{Count: 9}
	if err := json.Unmarshal([]byte(`{"name":"new"}`), &target); err != nil {
		t.Fatal(err)
	}
	if target.Count != 9 {
		t.Fatal("缺失字段保持目标原值；Unmarshal 不会先清零整个 struct")
	}
}
