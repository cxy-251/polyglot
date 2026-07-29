# 共同问题：stream 怎样分块、何时显式 flush，满缓冲怎样发出 backpressure。
# 输入：StringIO、IO.pipe、readpartial、write_nonblock 和 EOF；观察：同步字节结果、:wait_writable 及关闭信号。
# polyglot-family: files_paths_and_streams
# polyglot-concept: streaming_buffering_and_backpressure
# polyglot-related: languages/ruby/standard_library/09_files_io_and_process/
# polyglot-related+: test_067_io_pipes_binary_and_text_encoding.rb

require "assertions"
require "stringio"

A = PolyglotAssertions

buffer = StringIO.new
buffer.write("ruby")
A.equal(4, buffer.pos)
buffer.rewind
A.equal("ru", buffer.read(2))
A.equal("by", buffer.readpartial(2))
A.raises(EOFError) { buffer.readpartial(1) }

reader, writer = IO.pipe
begin
  chunk = "x" * 4096
  result = nil
  10_000.times do
    result = writer.write_nonblock(chunk, exception: false)
    break if result == :wait_writable
  end
  A.equal(:wait_writable, result)
  A.truth(IO.select(nil, [writer], nil, 0).nil?)
  A.truth(reader.read_nonblock(4096).bytesize.positive?)
  A.truth(IO.select(nil, [writer], nil, 0))
ensure
  reader.close
  writer.close
end

A.done
