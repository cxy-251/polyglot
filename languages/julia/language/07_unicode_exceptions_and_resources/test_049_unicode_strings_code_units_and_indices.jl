# polyglot-covers: julia.language.unicode-indices-substrings-and-search

using Test

@testset "String 索引定位 code unit；SubString 与搜索保留合法索引" begin
    text = "α🙂"
    @test length(text) == 2
    @test ncodeunits(text) == 6
    @test collect(eachindex(text)) == [1, 3]
    @test text[1] == 'α'
    @test text[3] == '🙂'
    @test_throws StringIndexError text[2]
    phrase = "alpha-beta-alpha"
    prefix = SubString(phrase, 1, 5)
    @test prefix == "alpha"
    @test prefix isa SubString
    @test findfirst("beta", phrase) == 7:10
    @test replace(phrase, "alpha" => "A"; count = 1) == "A-beta-alpha"
end
