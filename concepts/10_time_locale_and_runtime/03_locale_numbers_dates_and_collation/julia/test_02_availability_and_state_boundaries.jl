# polyglot-family: time_locale_and_runtime
# polyglot-concept: locale_numbers_dates_and_collation
# polyglot-related: languages/julia/tooling_and_runtime/15_reflection_time_and_runtime_observations/
# polyglot-related+: test_120_capability_detection_without_version_parsing.jl
#
# 共同问题：locale 能力怎样检测；测试是否应修改进程全局 locale。
# 对照观察：标准库没有 ICU collation 接口；通过 binding/package 查询表达缺失，不改写 ENV 或 libc locale。

using Test

@testset "locale 扩展能力以查询而非全局修改表达" begin
    original = copy(ENV)
    @test Base.find_package("ICU") === nothing
    @test !isdefined(Base, :Collator)
    @test ENV == original
end
