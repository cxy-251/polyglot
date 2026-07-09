using Test

@testset "Dict lookup helpers" begin
    counts = Dict("red" => 2, "blue" => 1)

    @test haskey(counts, "red")
    @test get(counts, "green", 0) == 0
    @test sort(collect(keys(counts))) == ["blue", "red"]
end
