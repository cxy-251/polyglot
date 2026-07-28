# polyglot-family: files_paths_and_streams
# polyglot-concept: process_environment_and_subprocess_io
# polyglot-related: languages/julia/standard_library/10_io_files_processes_and_networking/
# polyglot-related+: test_078_child_environment_and_working_directory.jl
#
# 共同问题：child 的环境、cwd、stdin/stdout 如何隔离；父进程状态是否被调用修改。
# 对照观察：Cmd 可用 addenv/setenv 和 dir 建立 child 状态，pipeline 显式连接 IO，父 ENV/cwd 保持不变。

using Test

@testset "child process 拥有显式环境和 IO 边界" begin
    parent_cwd = pwd()
    parent_value = get(ENV, "POLYGLOT_CHILD_ONLY", nothing)
    mktempdir(prefix = "polyglot-julia-") do directory
        script = "print(get(ENV, \"POLYGLOT_CHILD_ONLY\", \"missing\"), '|', basename(pwd()))"
        command = Cmd(`$(Base.julia_cmd()) --startup-file=no --history-file=no -e $script`; dir = directory)
        output = read(addenv(command, "POLYGLOT_CHILD_ONLY" => "child"), String)
        @test output == "child|" * basename(directory)
    end
    @test pwd() == parent_cwd
    @test get(ENV, "POLYGLOT_CHILD_ONLY", nothing) == parent_value
end
