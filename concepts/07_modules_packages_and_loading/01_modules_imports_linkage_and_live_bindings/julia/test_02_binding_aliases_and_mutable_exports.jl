# polyglot-family: modules_packages_and_loading
# polyglot-concept: modules_imports_linkage_and_live_bindings
# polyglot-related: languages/julia/tooling_and_runtime/11_modules_macros_and_metaprogramming/
# polyglot-related+: test_081_module_namespaces_exports_and_qualification.jl
#
# 共同问题：导入别名能否重新绑定；导出可变对象的内部修改是否对所有引用可见。
# 对照观察：imported binding 只读，调用方可建立自己的 const alias；对象 mutation 与 binding 重绑定分离。

using Test

module AliasSource
export state
const state = Dict(:count => 0)
end

const local_state_alias = AliasSource.state

@testset "alias 共享对象但拥有独立名称" begin
    local_state_alias[:count] += 1
    @test AliasSource.state[:count] == 1
    @test local_state_alias === AliasSource.state
    @test isconst(AliasSource, :state)
end
