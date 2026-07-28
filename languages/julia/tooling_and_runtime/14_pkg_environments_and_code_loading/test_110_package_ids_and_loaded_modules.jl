# polyglot-covers: julia.tooling.package-ids-and-loaded-modules

using Test
using PolyglotJuliaCourse

@testset "PkgId 将包名与 UUID 结合，module object 表示当前已加载实例" begin
    package_id = Base.PkgId(PolyglotJuliaCourse)
    @test package_id.name == "PolyglotJuliaCourse"
    @test string(package_id.uuid) == "3f74011e-5aac-4ad9-87ef-d9a12f0f19d2"
    @test Base.root_module(package_id) === PolyglotJuliaCourse
    @test parentmodule(PolyglotJuliaCourse.locked_version) === PolyglotJuliaCourse
end
