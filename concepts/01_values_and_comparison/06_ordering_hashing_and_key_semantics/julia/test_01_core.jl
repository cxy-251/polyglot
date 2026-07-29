# polyglot-family: values_and_comparison
# polyglot-concept: ordering_hashing_and_key_semantics
# polyglot-related: languages/julia/language/02_values_types_missing_and_numbers/
# polyglot-related+: test_012_equality_identity_and_nan.jl
#
# 共同问题：排序、哈希和映射键相等采用哪些协议；特殊数值能否稳定作为键。
# 对照观察：排序使用 isless，Dict/Set 使用 isequal 与 hash，因此 NaN 和 signed zero 有明确键语义。

using Test

@testset "顺序协议与键协议分离" begin
    values = [3, 1, 2]
    @test sort(values) == [1, 2, 3]
    keys = Dict(NaN => "nan", -0.0 => "negative")
    @test keys[NaN] == "nan"
    @test keys[-0.0] == "negative"
    @test !haskey(keys, 0.0)
    @test isequal(-0.0, 0.0) == false
end
