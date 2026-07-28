# polyglot-covers: julia.stdlib.unicode-normalization-and-graphemes

using Test
using Unicode

@testset "Unicode normalization 与 grapheme segmentation 独立于 codepoint 计数" begin
    composed = "é"
    decomposed = "e\u0301"
    @test composed != decomposed
    @test Unicode.normalize(decomposed, :NFC) == composed
    @test Unicode.normalize(composed, :NFD) == decomposed
    @test length(decomposed) == 2
    @test collect(Unicode.graphemes(decomposed)) == [decomposed]
end
