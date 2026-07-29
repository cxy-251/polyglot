# polyglot-covers: julia.runtime.type-method-and-documentation-reflection

using Test
using Base.Docs

struct RuntimePair{T}
    left::T
    right::T
end

runtime_method(value::Int) = value + 1
runtime_method(value::AbstractString) = uppercase(value)

@testset "结构化反射分别查询类型、method applicability 与文档元数据" begin
    @test fieldnames(RuntimePair) == (:left, :right)
    @test fieldtypes(RuntimePair{Int}) == (Int, Int)
    @test RuntimePair{Int}.parameters[1] === Int
    @test isconcretetype(RuntimePair{Int})
    @test !isconcretetype(RuntimePair)
    @test length(methods(runtime_method)) == 2
    @test which(runtime_method, (Int,)).name === :runtime_method
    @test applicable(runtime_method, 1)
    @test !applicable(runtime_method, 1.0)
    @test hasmethod(runtime_method, Tuple{AbstractString})
    @test (@doc sin) !== nothing
    @test nameof(sin) === :sin
    @test parentmodule(sin) === Base
end
