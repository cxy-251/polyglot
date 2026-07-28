# polyglot-covers: julia.language.hash-dict-and-set-semantics

using Test

@testset "Dict 与 Set 的键语义采用 isequal 和 hash" begin
    mapping = Dict(NaN => "unknown", missing => "missing")
    @test mapping[NaN] == "unknown"
    @test mapping[missing] == "missing"
    @test length(Set([NaN, NaN])) == 1
    @test hash((1, 2)) == hash((1, 2))
    @test Dict(-0.0 => :negative, 0.0 => :positive) |> length == 2
end
