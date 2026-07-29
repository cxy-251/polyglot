# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.loopback-socket-protocol

require "assertions"
require "socket"

A = PolyglotAssertions

server = TCPServer.new("127.0.0.1", 0)
worker = Thread.new do
  connection = server.accept
  request = connection.gets
  connection.write("reply:#{request}")
  connection.close
  request
end

client = TCPSocket.new("127.0.0.1", server.local_address.ip_port)
client.write("ruby\n")
client.close_write
response = client.read
client.close

A.equal("reply:ruby\n", response)
A.equal("ruby\n", worker.value)
A.falsey(worker.alive?)
server.close
A.truth(server.closed?)

A.done
