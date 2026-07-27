// polyglot-covers: go.unsafe.pointer-gc-finalizer-boundaries
package runtimeintrospection_test

import (
	"runtime"
	"testing"
	"unsafe"
)

type finalizableValue struct{ number int }

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
