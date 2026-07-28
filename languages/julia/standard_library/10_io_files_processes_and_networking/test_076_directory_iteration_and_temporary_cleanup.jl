# polyglot-covers: julia.stdlib.directory-iteration-and-temporary-cleanup

using Test

@testset "目录遍历返回显式路径，mktempdir do block 负责清理" begin
    remembered_path = Ref("")
    mktempdir(prefix = "polyglot-julia-") do directory
        remembered_path[] = directory
        mkpath(joinpath(directory, "nested"))
        write(joinpath(directory, "a.txt"), "a")
        write(joinpath(directory, "nested", "b.txt"), "b")
        files = String[]
        for (root, _, names) in walkdir(directory)
            append!(files, joinpath.(root, names))
        end
        @test sort(basename.(files)) == ["a.txt", "b.txt"]
    end
    @test !ispath(remembered_path[])
end
