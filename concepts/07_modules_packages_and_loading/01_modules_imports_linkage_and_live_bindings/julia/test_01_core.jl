# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/julia/tooling_and_runtime/11_modules_macros_and_metaprogramming/
# polyglot-related+: test_081_module_namespaces_exports_and_qualification.jl
#
# 共同问题：module 怎样建立 namespace；导入或别名共享 binding 还是只共享可变对象。
# 对照观察：qualified access 指向模块 binding；本地 alias 共享对象但拥有独立名称，export 只影响名称引入。

using Test

module LiveSource
export shared
const shared = Int[1]
hidden = 2
end

@testset "模块限定名保持同一可变导出对象" begin
    local_alias = LiveSource.shared
    push!(LiveSource.shared, 2)
    @test local_alias === LiveSource.shared
    @test local_alias == [1, 2]
    @test LiveSource.hidden == 2
    @test Base.isexported(LiveSource, :shared)
    @test !Base.isexported(LiveSource, :hidden)
    @test isconst(LiveSource, :shared)
end
