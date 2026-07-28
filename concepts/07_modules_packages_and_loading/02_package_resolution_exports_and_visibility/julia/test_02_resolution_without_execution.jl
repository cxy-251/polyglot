# polyglot-family: modules_packages_and_loading
# polyglot-concept: package_resolution_exports_and_visibility
# polyglot-related: languages/julia/tooling_and_runtime/14_pkg_environments_and_code_loading/
# polyglot-related+: test_109_find_package_and_source_identity.jl
#
# 共同问题：能否只解析 package 来源而不执行初始化；解析结果怎样表达不存在。
# 对照观察：Base.find_package 查询当前 LOAD_PATH 的入口路径，不执行源码；找不到时返回 nothing。

using Test

@testset "解析查询不向 Main 注入 module binding" begin
    @test !isdefined(Main, :Dates)
    path = Base.find_package("Dates")
    @test path isa String
    @test endswith(path, "Dates.jl")
    @test !isdefined(Main, :Dates)
    @test Base.find_package("PolyglotDefinitelyMissing") === nothing
end
