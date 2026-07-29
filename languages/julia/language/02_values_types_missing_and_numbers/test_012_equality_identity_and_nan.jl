# polyglot-covers: julia.language.equality-identity-hash-and-keys

using Test

@testset "值相等、身份与键相等采用不同协议" begin
    first = [1, 2]
    second = [1, 2]
    @test first == second
    @test first !== second
    @test isequal(NaN, NaN)
    @test NaN != NaN
    @test isequal(-0.0, 0.0) === false
    @test -0.0 == 0.0
    mapping = Dict(NaN => "unknown", missing => "missing")
    @test mapping[NaN] == "unknown"
    @test mapping[missing] == "missing"
    @test length(Set([NaN, NaN])) == 1
    @test Dict(-0.0 => :negative, 0.0 => :positive) |> length == 2
    @test hash((1, 2)) == hash((1, 2))
end
