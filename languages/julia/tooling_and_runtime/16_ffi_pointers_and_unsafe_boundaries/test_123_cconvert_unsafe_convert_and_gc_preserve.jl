# polyglot-covers: julia.runtime.pointer-conversion-storage-and-gc-lifetime

using Test

mutable struct PointerBox
    value::Int
end

@testset "pointer 操作要求拥有存储，并在整个使用期保活原 Julia 对象" begin
    converted = Base.cconvert(Cstring, "hello")
    pointer = Base.unsafe_convert(Cstring, converted)
    GC.@preserve converted begin
        @test unsafe_string(pointer) == "hello"
        @test unsafe_load(Ptr{UInt8}(pointer)) == UInt8('h')
    end
    reference = Ref{Cint}(7)
    reference_pointer = Base.unsafe_convert(Ptr{Cint}, reference)
    GC.@preserve reference begin
        @test unsafe_load(reference_pointer) == 7
        unsafe_store!(reference_pointer, 9)
        @test reference[] == 9
    end
    box = PointerBox(7)
    GC.@preserve box begin
        object_pointer = pointer_from_objref(box)
        restored = unsafe_pointer_to_objref(object_pointer)
        @test restored === box
        @test restored.value == 7
    end
end
