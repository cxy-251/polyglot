// polyglot-covers: go.encoding-json.custom-and-raw-message
package serialization_test

import (
	"encoding/json"
	"strings"
	"testing"
)

type upperText string

func (value upperText) MarshalJSON() ([]byte, error) {
	return json.Marshal(strings.ToUpper(string(value)))
}

func TestCustomMarshalerAndRawMessageControlRepresentation(t *testing.T) {
	payload := struct {
		Label upperText       `json:"label"`
		Extra json.RawMessage `json:"extra"`
	}{Label: "go", Extra: json.RawMessage(`{"version":1}`)}
	encoded, err := json.Marshal(payload)
	if err != nil || string(encoded) != `{"label":"GO","extra":{"version":1}}` {
		t.Fatalf("Marshaler 定义字段表示；RawMessage 延迟局部解码: %s %v", encoded, err)
	}
}
