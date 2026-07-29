# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.net-http-loopback-only

require "assertions"
require "net/http"
require "socket"

A = PolyglotAssertions

server = TCPServer.new("127.0.0.1", 0)
worker = Thread.new do
  connection = server.accept
  request_line = connection.gets
  while (header_line = connection.gets)
    break if header_line.chomp.empty?
  end
  body = "ruby"
  connection.write("HTTP/1.1 200 OK\r\nContent-Length: #{body.bytesize}\r\n\r\n#{body}")
  connection.close
  request_line
end

port = server.local_address.ip_port
http = Net::HTTP.new("127.0.0.1", port, nil)
response = http.get("/course")
A.equal("200", response.code)
A.equal("ruby", response.body)
A.truth(worker.value.start_with?("GET /course "))
server.close
A.truth(server.closed?)

A.done
