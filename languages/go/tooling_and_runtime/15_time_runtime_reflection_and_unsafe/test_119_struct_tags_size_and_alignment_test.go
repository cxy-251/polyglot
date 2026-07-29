// polyglot-covers: go.unsafe.layout-pointer-and-gc-lifetime-boundaries
package runtimeintrospection_test

import (
	"reflect"
	"runtime"
	"testing"
	"unsafe"
)

type taggedLayout struct {
	Flag byte   `json:"flag"`
	Name string `json:"name,omitempty"`
}

type finalizableValue struct{ number int }

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

func TestUnsafePointerArithmeticMustStayWithinOneObject(t *testing.T) {
	values := [2]uint32{10, 20}
	first := unsafe.Pointer(&values[0])
	second := (*uint32)(unsafe.Add(first, unsafe.Sizeof(values[0])))
	if *second != 20 {
		t.Fatal("unsafe.Add 可在同一分配对象内按 byte offset 定位")
	}

	value := &finalizableValue{number: 7}
	runtime.SetFinalizer(value, func(*finalizableValue) {})
	runtime.KeepAlive(value)
	runtime.SetFinalizer(value, nil)
	// finalizer 的调度和进程退出前执行都无保证，不能用作必须发生的资源清理。
}
