# 共同问题：相对路径、dot segment、分隔符和绝对解析怎样处理。
# 输入：Pathname、cleanpath、expand_path、basename 和 cwd；观察：词法规范化、进程 cwd 解析及平台分隔符。
# polyglot-family: files_paths_and_streams
# polyglot-concept: path_normalization_and_resolution
# polyglot-related: languages/ruby/standard_library/09_files_io_and_process/test_065_file_dir_and_pathname.rb

require "assertions"
require "pathname"

A = PolyglotAssertions

relative = Pathname("alpha/./beta/../value.txt")
A.equal("alpha/value.txt", relative.cleanpath.to_s)
A.equal(File.join(Dir.pwd, "alpha", "value.txt"), File.expand_path(relative.cleanpath))
A.equal("value.txt", relative.basename.to_s)
A.equal("alpha/.", Pathname("alpha/.").to_s)
A.equal(File::SEPARATOR, "/")
A.falsey(relative.absolute?)
A.truth(Pathname(File.expand_path(relative)).absolute?)

A.done
