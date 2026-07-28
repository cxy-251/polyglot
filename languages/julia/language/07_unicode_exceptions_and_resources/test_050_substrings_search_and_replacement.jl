# polyglot-covers: julia.language.substrings-search-and-replacement

using Test

@testset "SubString 表示字符串视图，搜索结果使用合法字符串索引" begin
    text = "alpha-beta-alpha"
    prefix = SubString(text, 1, 5)
    @test prefix == "alpha"
    @test prefix isa SubString
    @test findfirst("beta", text) == 7:10
    @test replace(text, "alpha" => "A"; count = 1) == "A-beta-alpha"
    @test occursin(r"beta", text)
end
