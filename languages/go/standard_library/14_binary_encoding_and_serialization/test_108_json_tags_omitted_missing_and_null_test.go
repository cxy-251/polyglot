// polyglot-covers: go.encoding-json.tags-omitted-missing-null
package serialization_test

import (
	"encoding/json"
	"testing"
)

type jsonRecord struct {
	Name  string  `json:"name"`
	Count int     `json:"count,omitempty"`
	Note  *string `json:"note"`
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
