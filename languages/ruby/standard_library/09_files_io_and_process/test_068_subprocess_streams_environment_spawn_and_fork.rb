# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.open3-subprocess-streams-and-status

require "assertions"
require "open3"
require "rbconfig"

A = PolyglotAssertions

A.case("Open3.capture3 exchanges standard streams and a child-only environment") do
  stdout, stderr, status = Open3.capture3(
    {"POLYGLOT_CHILD" => "capture"},
    RbConfig.ruby,
    "-e",
    "STDOUT.write(ENV.fetch('POLYGLOT_CHILD') + ':' + STDIN.read.upcase); STDERR.write('note')",
    stdin_data: "ruby"
  )
  A.equal("capture:RUBY", stdout)
  A.equal("note", stderr)
  A.truth(status.success?)
  A.nil_value(ENV["POLYGLOT_CHILD"])
end

A.case("Process.spawn returns a PID that wait2 pairs with its exit status") do
  read_end, write_end = IO.pipe
  pid = Process.spawn(
    {"POLYGLOT_CHILD" => "spawn"},
    RbConfig.ruby,
    "-e",
    "print ENV.fetch('POLYGLOT_CHILD')",
    out: write_end
  )
  write_end.close
  A.equal("spawn", read_end.read)
  read_end.close
  waited, child_status = Process.wait2(pid)
  A.equal(pid, waited)
  A.truth(child_status.success?)
ensure
  read_end&.close unless read_end&.closed?
  write_end&.close unless write_end&.closed?
  begin
    Process.wait(pid) if pid
  rescue Errno::ECHILD
    nil
  end
end

A.case("fork copies process state but the child has its own PID and collected status") do
  reader, writer = IO.pipe
  forked_pid = fork do
    reader.close
    writer.write(Process.pid.to_s)
    writer.close
    exit! 0
  end
  writer.close
  A.equal(forked_pid, Integer(reader.read))
  reader.close
  waited, fork_status = Process.wait2(forked_pid)
  A.equal(forked_pid, waited)
  A.truth(fork_status.success?)
ensure
  reader&.close unless reader&.closed?
  writer&.close unless writer&.closed?
  begin
    Process.wait(forked_pid) if forked_pid
  rescue Errno::ECHILD
    nil
  end
end

A.done
