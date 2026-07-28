# polyglot-covers: julia.runtime.pointer-from-objref-and-object-lifetime

using Test

mutable struct PointerBox
    value::Int
end

@testset "pointer_from_objref 只适用于保活的 mutable object" begin
    box = PointerBox(7)
    GC.@preserve box begin
        pointer = pointer_from_objref(box)
        restored = unsafe_pointer_to_objref(pointer)
        @test restored === box
        @test restored.value == 7
    end
end
