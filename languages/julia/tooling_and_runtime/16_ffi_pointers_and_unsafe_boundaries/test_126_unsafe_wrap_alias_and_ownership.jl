# polyglot-covers: julia.runtime.unsafe-wrap-alias-and-ownership

using Test

@testset "unsafe_wrap own=false 建立别名且不接管原数组存储" begin
    storage = Int32[1, 2, 3]
    GC.@preserve storage begin
        storage_pointer = pointer(storage)
        alias = unsafe_wrap(Vector{Int32}, storage_pointer, length(storage); own = false)
        @test alias == storage
        alias[2] = 9
        @test storage == Int32[1, 9, 3]
        @test pointer(alias) == storage_pointer
    end
end
