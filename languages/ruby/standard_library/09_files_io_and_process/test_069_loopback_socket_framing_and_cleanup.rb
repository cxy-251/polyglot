# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.loopback-socket-protocol

require "assertions"
require "socket"

A = PolyglotAssertions

A.case("a loopback TCP protocol frames a line and closes every endpoint") do
  server = TCPServer.new("127.0.0.1", 0)
  client = nil
  worker = Thread.new do
    connection = server.accept
    begin
      request = connection.gets
      connection.write("reply:#{request}")
      request
    ensure
      connection.close
    end
  end

  begin
    client = TCPSocket.new("127.0.0.1", server.local_address.ip_port)
    client.write("ruby\n")
    client.close_write
    A.equal("reply:ruby\n", client.read)
    A.equal("ruby\n", worker.value)
  ensure
    client&.close unless client&.closed?
    server.close unless server.closed?
  end
  A.falsey(worker.alive?)
  A.truth(server.closed?)
end

A.done
