# polyglot-covers: julia.language.equality-identity-and-nan

using Test

@testset "值相等、字典相等与对象身份使用不同协议" begin
    first = [1, 2]
    second = [1, 2]
    @test first == second
    @test first !== second
    @test isequal(NaN, NaN)
    @test NaN != NaN
    @test isequal(-0.0, 0.0) === false
    @test -0.0 == 0.0
end
