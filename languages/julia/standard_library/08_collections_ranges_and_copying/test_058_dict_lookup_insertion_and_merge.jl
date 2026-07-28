# polyglot-covers: julia.stdlib.dict-lookup-insertion-and-merge

using Test

@testset "Dict 区分只读 lookup、缺失默认值和插入路径" begin
    mapping = Dict(:a => 1)
    @test mapping[:a] == 1
    @test get(mapping, :missing, 0) == 0
    @test !haskey(mapping, :missing)
    inserted = get!(mapping, :b) do
        2
    end
    @test inserted == 2
    @test mapping == Dict(:a => 1, :b => 2)
    @test merge(mapping, Dict(:b => 20))[:b] == 20
end
