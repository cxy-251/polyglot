# polyglot-family: text_binary_and_serialization
# polyglot-concept: regular_expressions_and_state
# polyglot-related: languages/julia/language/07_unicode_exceptions_and_resources/
# polyglot-related+: test_053_regular_expressions_and_match_state.jl
#
# 共同问题：匹配结果携带哪些局部状态；重复搜索是否修改共享 pattern。
# 对照观察：Regex 可复用，match/eachmatch 返回独立 RegexMatch；失败返回 nothing。

using Test

@testset "匹配位置和 captures 属于结果对象" begin
    pattern = r"(?<word>\p{L}+)"
    first_match = match(pattern, "Julia 语言")
    @test first_match.match == "Julia"
    @test first_match[:word] == "Julia"
    @test first_match.offset == 1
    @test getproperty.(collect(eachmatch(pattern, "a b")), :match) == ["a", "b"]
    @test match(pattern, "123") === nothing
end
