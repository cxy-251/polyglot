# polyglot-covers: julia.stdlib.dict-lookup-insertion-and-merge

using Test

@testset "Dict 区分只读 lookup、缺失默认值和插入路径" begin
    mapping = Dict(:a => 1)
    @test mapping[:a] == 1
    @test_throws KeyError mapping[:missing]
    @test get(mapping, :missing, 0) == 0
    @test !haskey(mapping, :missing)
    evaluations = Ref(0)
    inserted = get!(mapping, :b) do
        evaluations[] += 1
        2
    end
    @test inserted == 2
    @test get!(() -> (evaluations[] += 1), mapping, :b) == 2
    @test evaluations[] == 1
    @test mapping == Dict(:a => 1, :b => 2)
    @test merge(mapping, Dict(:b => 20))[:b] == 20
end
