# polyglot-family: text_binary_and_serialization
# polyglot-concept: unicode_strings_and_code_units
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_049_unicode_strings_code_units_and_indices.jl
#
# 共同问题：文本长度按字节、码点还是 grapheme 计算；随机索引是否总是有效。
# 对照观察：Julia String 是 UTF-8 code units；length 迭代码点，合法索引定位字符起始字节。

using Test

@testset "code unit 数和字符迭代数独立" begin
    text = "Aλ🙂"
    @test ncodeunits(text) == 7
    @test length(text) == 3
    @test collect(codeunits(text)) == UInt8[0x41, 0xce, 0xbb, 0xf0, 0x9f, 0x99, 0x82]
    @test text[nextind(text, firstindex(text))] == 'λ'
    @test_throws StringIndexError text[3]
end
