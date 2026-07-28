# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/julia/tooling_and_runtime/11_modules_macros_and_metaprogramming/
# polyglot-related+: test_081_module_namespaces_exports_and_qualification.jl
#
# 共同问题：module 怎样建立 namespace；imported 名称是值快照还是同一 binding。
# 对照观察：Julia using/import 绑定模块中的 global，qualified access 始终指向模块；export 只影响名称引入。

using Test

module LiveSource
export shared
const shared = Int[1]
hidden = 2
end

@testset "模块限定名保持同一可变导出对象" begin
    alias = LiveSource.shared
    push!(LiveSource.shared, 2)
    @test alias === LiveSource.shared
    @test alias == [1, 2]
    @test LiveSource.hidden == 2
    @test Base.isexported(LiveSource, :shared)
    @test !Base.isexported(LiveSource, :hidden)
end
