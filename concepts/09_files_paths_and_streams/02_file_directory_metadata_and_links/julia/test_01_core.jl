# polyglot-family: files_paths_and_streams
# polyglot-concept: file_directory_metadata_and_links
# polyglot-related: languages/julia/standard_library/10_io_files_processes_and_networking/
# polyglot-related+: test_075_file_metadata_links_and_permissions.jl
#
# 共同问题：file、directory 与 symlink 的元数据怎样区分；删除 link 是否影响 target。
# 对照观察：stat 跟随链接，lstat 观察链接本身；rm(link) 只删除目录项，不删除目标。

using Test

@testset "stat 和 lstat 观察不同对象层" begin
    mktempdir(prefix = "polyglot-julia-") do directory
        target = joinpath(directory, "target")
        write(target, "payload")
        link = joinpath(directory, "link")
        symlink(target, link)
        @test isfile(stat(link))
        @test islink(lstat(link))
        rm(link)
        @test isfile(target)
        @test !ispath(link)
    end
end
