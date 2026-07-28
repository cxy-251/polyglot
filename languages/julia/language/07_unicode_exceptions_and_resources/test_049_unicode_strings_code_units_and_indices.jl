# polyglot-covers: julia.language.unicode-strings-code-units-and-indices

using Test

@testset "String 索引定位字符起始 code unit 而不是字符序号" begin
    text = "α🙂"
    @test length(text) == 2
    @test ncodeunits(text) == 6
    @test collect(eachindex(text)) == [1, 3]
    @test text[1] == 'α'
    @test text[3] == '🙂'
    @test_throws StringIndexError text[2]
end
