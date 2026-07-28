# polyglot-covers: julia.stdlib.loopback-sockets-and-explicit-protocols

using Test
using Sockets

@testset "loopback socket 使用动态端口和明确请求响应协议" begin
    server = listen(ip"127.0.0.1", 0)
    _, port = getsockname(server)
    server_task = @async begin
        socket = accept(server)
        try
            request = readline(socket)
            write(socket, uppercase(request), '\n')
        finally
            close(socket)
        end
    end
    client = connect(ip"127.0.0.1", port)
    try
        write(client, "hello\n")
        @test readline(client) == "HELLO"
    finally
        close(client)
        wait(server_task)
        close(server)
    end
    @test istaskdone(server_task)
end
