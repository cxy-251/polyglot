# polyglot-covers: julia.runtime.type-field-and-parameter-reflection

using Test

struct RuntimePair{T}
    left::T
    right::T
end

@testset "type reflection 返回字段、参数和 concrete 状态" begin
    @test fieldnames(RuntimePair) == (:left, :right)
    @test fieldtypes(RuntimePair{Int}) == (Int, Int)
    @test RuntimePair{Int}.parameters[1] === Int
    @test isconcretetype(RuntimePair{Int})
    @test !isconcretetype(RuntimePair)
end
