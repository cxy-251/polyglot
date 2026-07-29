# polyglot-family: modules_packages_and_loading
# polyglot-concept: initialization_caching_cycles_and_dynamic_loading
# polyglot-related: languages/julia/tooling_and_runtime/14_pkg_environments_and_code_loading/
# polyglot-related+: test_109_find_package_and_source_identity.jl
#
# 共同问题：加载失败是否污染成功缓存；后续解析能否区分未找到与已加载。
# 对照观察：不存在的 PkgId 使 require 失败且不会出现在 loaded_modules；find_package 仍返回 nothing。

using Test
using UUIDs

@testset "失败 require 不建立成功缓存项" begin
    package_id = Base.PkgId(UUID("d44df542-1aea-4fd6-80c0-f2c50d2a56ff"), "MissingPolyglotPackage")
    @test_throws ArgumentError Base.require(package_id)
    @test_throws ArgumentError Base.require(package_id)
    @test Base.find_package(package_id.name) === nothing
end
