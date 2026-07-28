# polyglot-family: modules_packages_and_loading
# polyglot-concept: package_resolution_exports_and_visibility
# polyglot-related: languages/julia/tooling_and_runtime/14_pkg_environments_and_code_loading/
# polyglot-related+: test_107_load_path_expansion_and_stdlib_fallback.jl
#
# 共同问题：package 怎样由环境解析；export 是否等于私有访问控制。
# 对照观察：LOAD_PATH 决定 package identity，export 只控制 using 引入；未导出 global 仍可 qualified 访问。

using Test

module VisibilityExample
export public_value
public_value = 1
internal_value = 2
end

@testset "export 是名称选择而非访问控制" begin
    @test Base.isexported(VisibilityExample, :public_value)
    @test !Base.isexported(VisibilityExample, :internal_value)
    @test VisibilityExample.internal_value == 2
    @test names(VisibilityExample) == [:VisibilityExample, :public_value]
end
