# polyglot-family: text_binary_and_serialization
# polyglot-concept: unicode_strings_and_code_units
# polyglot-related: languages/julia/standard_library/09_text_data_dates_and_math/
# polyglot-related+: test_065_unicode_normalization_and_graphemes.jl
#
# 共同问题：规范等价文本是否按字节相等；非法编码怎样进入字符串模型。
# 对照观察：Unicode.normalize 显式选择规范化；Julia String 可保存无效 UTF-8，isvalid 负责能力检测。

using Test
using Unicode

@testset "规范化与编码有效性是独立维度" begin
    composed = "é"
    decomposed = "e\u0301"
    @test composed != decomposed
    @test Unicode.normalize(decomposed, :NFC) == composed
    @test length(Unicode.graphemes(decomposed)) == 1
    invalid = String(UInt8[0xff])
    @test !isvalid(invalid)
    @test ncodeunits(invalid) == 1
end
