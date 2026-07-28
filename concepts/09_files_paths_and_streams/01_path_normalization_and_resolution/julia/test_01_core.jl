# polyglot-family: files_paths_and_streams
# polyglot-concept: path_normalization_and_resolution
# polyglot-related: languages/julia/standard_library/10_io_files_processes_and_networking/
# polyglot-related+: test_074_path_operations_and_canonicalization.jl
#
# 共同问题：词法规范化与文件系统解析如何区分；相对路径以哪个 cwd 为基准。
# 对照观察：normpath 只折叠语法片段，abspath 绑定 cwd，realpath 要求目标存在并解析链接。

using Test

@testset "路径操作按是否访问文件系统分层" begin
    @test normpath("a", "..", "b") == "b"
    mktempdir(prefix = "polyglot-julia-") do directory
        target = joinpath(directory, "target")
        write(target, "data")
        link = joinpath(directory, "link")
        symlink(target, link)
        @test realpath(link) == realpath(target)
        @test isabspath(abspath(target))
    end
end
