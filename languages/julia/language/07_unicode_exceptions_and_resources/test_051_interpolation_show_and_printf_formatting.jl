# polyglot-covers: julia.language.interpolation-show-and-printf-formatting

using Test
using Printf

@testset "插值、show 与 Printf 面向不同输出协议" begin
    value = 3
    @test "value=$(value + 1)" == "value=4"
    @test repr("line\n") == "\"line\\n\""
    @test sprint(print, "a", 1) == "a1"
    @test @sprintf("%.2f", 1.5) == "1.50"
end
