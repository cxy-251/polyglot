# polyglot-family: modules_packages_and_loading
# polyglot-concept: initialization_caching_cycles_and_dynamic_loading
# polyglot-related: languages/julia/tooling_and_runtime/14_pkg_environments_and_code_loading/
# polyglot-related+: test_110_package_ids_and_loaded_modules.jl
#
# 共同问题：重复加载是否重复初始化；缓存按名称、路径还是 package identity 建立。
# 对照观察：Base.require 按 PkgId 缓存 module object；已加载标准库的重复 require 返回同一实例。

using Test

@testset "PkgId 缓存同一已加载 module" begin
    package_id = Base.PkgId(Test)
    first = Base.require(package_id)
    second = Base.require(package_id)
    @test first === Test
    @test second === Test
    @test first === second
    @test Base.loaded_modules[package_id] === Test
end
