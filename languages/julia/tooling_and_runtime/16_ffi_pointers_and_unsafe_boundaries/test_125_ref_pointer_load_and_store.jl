# polyglot-covers: julia.runtime.ref-pointer-load-and-store

using Test

@testset "Ref 提供拥有存储，unsafe_load/store 需要调用方证明 pointer 有效" begin
    reference = Ref{Cint}(7)
    pointer = Base.unsafe_convert(Ptr{Cint}, reference)
    GC.@preserve reference begin
        @test unsafe_load(pointer) == 7
        unsafe_store!(pointer, 9)
        @test reference[] == 9
    end
end
