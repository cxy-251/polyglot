# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.net-http-loopback-only

require "assertions"
require "net/http"
require "socket"
require "uri"

A = PolyglotAssertions

A.case("URI parses components and rejects an unescaped space") do
  uri = URI("https://example.test:8443/path?q=ruby#part")
  A.equal(
    ["https", "example.test", 8443, "/path", "q=ruby"],
    [uri.scheme, uri.host, uri.port, uri.path, uri.query]
  )
  A.raises(URI::InvalidURIError) { URI("https://example.test/a b") }
end

A.case("Net::HTTP exchanges one request over a loopback HTTP/1.1 server") do
  server = TCPServer.new("127.0.0.1", 0)
  worker = Thread.new do
    connection = server.accept
    begin
      request_line = connection.gets
      while (header_line = connection.gets)
        break if header_line == "\r\n"
      end
      body = "ruby"
      connection.write("HTTP/1.1 200 OK\r\nContent-Length: #{body.bytesize}\r\nConnection: close\r\n\r\n#{body}")
      request_line
    ensure
      connection.close
    end
  end

  begin
    http = Net::HTTP.new("127.0.0.1", server.local_address.ip_port, nil)
    response = http.get("/course")
    A.equal("200", response.code)
    A.equal("ruby", response.body)
    A.truth(worker.value.start_with?("GET /course "))
  ensure
    server.close unless server.closed?
  end
  A.truth(server.closed?)
end

A.done
