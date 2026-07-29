# polyglot-covers: julia.language.text-formatting-parsing-and-failure

using Test
using Printf

@testset "格式化协议与文本解析的失败通道保持分离" begin
    value = 3
    @test "value=$(value + 1)" == "value=4"
    @test repr("line\n") == "\"line\\n\""
    @test sprint(print, "a", 1) == "a1"
    @test @sprintf("%.2f", 1.5) == "1.50"
    @test parse(Int, "42") == 42
    @test parse(Float64, "1.5") == 1.5
    @test tryparse(Int, "invalid") === nothing
    @test_throws ArgumentError parse(Int, "invalid")
end
