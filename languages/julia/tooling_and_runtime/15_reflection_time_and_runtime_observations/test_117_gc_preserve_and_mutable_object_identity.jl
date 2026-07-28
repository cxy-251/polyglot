# polyglot-covers: julia.runtime.gc-and-mutable-object-identity

using Test

mutable struct RuntimeBox
    value::Int
end

@testset "objectid 标识当前进程的 mutable 对象，不作为持久标识" begin
    box = RuntimeBox(1)
    alias = box
    identity = objectid(box)
    GC.gc()
    @test alias === box
    @test objectid(alias) == identity
    @test RuntimeBox(1) !== box
end
