# polyglot-family: time_locale_and_runtime
# polyglot-concept: runtime_capabilities_versions_and_feature_detection
# polyglot-related: languages/julia/tooling_and_runtime/15_reflection_time_and_runtime_observations/
# polyglot-related+: test_113_version_machine_and_platform_queries.jl
#
# 共同问题：版本、平台和 API 能力怎样查询；何时应按版本分支。
# 对照观察：VERSION/Sys 提供结构化事实；isdefined/hasmethod/applicable 直接检测所需接口。

using Test

@testset "能力查询优先于字符串版本解析" begin
    @test VERSION == v"1.12.6"
    @test Sys.WORD_SIZE in (32, 64)
    @test isdefined(Base, :ScopedValues)
    @test hasmethod(timedwait, Tuple{Function,Real})
    @test applicable(iterate, 1:3)
end
