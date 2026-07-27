// polyglot-covers: go.reflect.struct-tags-unsafe-layout
package runtimeintrospection_test

import (
	"reflect"
	"testing"
	"unsafe"
)

type taggedLayout struct {
	Flag byte   `json:"flag"`
	Name string `json:"name,omitempty"`
}

func TestStructTagsAreMetadataAndAlignmentAffectsSize(t *testing.T) {
	field, ok := reflect.TypeOf(taggedLayout{}).FieldByName("Name")
	if !ok || field.Tag.Get("json") != "name,omitempty" {
		t.Fatal("struct tag 是编译进类型的字符串元数据，由库自行解释")
	}
	var value taggedLayout
	if unsafe.Alignof(value) < unsafe.Alignof(value.Name) ||
		unsafe.Sizeof(value) < unsafe.Sizeof(value.Flag)+unsafe.Sizeof(value.Name) {
		t.Fatal("struct 尺寸包含满足字段 alignment 的 padding")
	}
}
