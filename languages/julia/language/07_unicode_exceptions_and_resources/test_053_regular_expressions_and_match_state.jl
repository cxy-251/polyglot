# polyglot-covers: julia.language.regular-expressions-and-match-state

using Test

@testset "Regex match 返回局部匹配对象而不修改模式全局状态" begin
    pattern = r"(?<name>[a-z]+)=(?<value>\d+)"
    first_match = match(pattern, "x=10")
    second_match = match(pattern, "y=20")
    @test first_match["name"] == "x"
    @test first_match["value"] == "10"
    @test second_match.captures == ["y", "20"]
    @test match(pattern, "missing") === nothing
end
