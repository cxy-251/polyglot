# 共同问题：环境变量、subprocess stdin/stdout/stderr 和退出状态怎样暴露。
# 输入：隔离 env、Open3.capture3、成功与非零退出；观察：字符串继承、完整捕获和 Process::Status。
# polyglot-family: files_paths_and_streams
# polyglot-concept: process_environment_and_subprocess_io
# polyglot-related: languages/ruby/standard_library/09_files_io_and_process/
# polyglot-related+: test_068_subprocess_streams_environment_spawn_and_fork.rb

require "assertions"
require "open3"
require "rbconfig"

A = PolyglotAssertions

environment = {"POLYGLOT_CHILD_VALUE" => "ruby"}
stdout, stderr, status = Open3.capture3(
  environment,
  RbConfig.ruby,
  "-e",
  "STDOUT.write(ENV.fetch('POLYGLOT_CHILD_VALUE') + ':' + STDIN.read); STDERR.write('note')",
  stdin_data: "input"
)
A.equal("ruby:input", stdout)
A.equal("note", stderr)
A.truth(status.success?)
A.equal(0, status.exitstatus)
A.nil_value(ENV["POLYGLOT_CHILD_VALUE"])

_stdout, _stderr, failed = Open3.capture3(RbConfig.ruby, "-e", "exit 7")
A.falsey(failed.success?)
A.equal(7, failed.exitstatus)

A.done
