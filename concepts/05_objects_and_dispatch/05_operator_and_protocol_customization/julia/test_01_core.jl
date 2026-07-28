# polyglot-family: objects_and_dispatch
# polyglot-concept: operator_and_protocol_customization
# polyglot-related: languages/julia/language/04_multiple_dispatch_methods_and_world_age/
# polyglot-related+: test_025_multiple_dispatch_across_arguments.jl
#
# 共同问题：用户类型怎样接入运算符和容器协议；相等与哈希如何保持一致。
# 对照观察：Julia 运算符是普通 generic function；为值类型定义 == 时同步定义 isequal/hash 才能安全作键。

using Test

struct Token
    value::Int
end

Base.:+(left::Token, right::Token) = Token(left.value + right.value)
Base.:(==)(left::Token, right::Token) = left.value == right.value
Base.isequal(left::Token, right::Token) = isequal(left.value, right.value)
Base.hash(token::Token, seed::UInt) = hash(token.value, seed)

@testset "运算符扩展进入普通 dispatch 和键协议" begin
    @test Token(1) + Token(2) == Token(3)
    mapping = Dict(Token(1) => "one")
    @test mapping[Token(1)] == "one"
    @test applicable(+, Token(1), Token(2))
end
