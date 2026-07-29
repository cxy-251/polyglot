# 共同问题：文件、目录、metadata、hard link 和 symbolic link 怎样观测。
# 输入：临时树、stat/lstat、link、symlink、rename 和 delete；观察：inode 身份、link 类型及真实目标。
# polyglot-family: files_paths_and_streams
# polyglot-concept: file_directory_metadata_and_links
# polyglot-related: languages/ruby/standard_library/09_files_io_and_process/test_071_metadata_links_and_realpath.rb

require "assertions"
require "fileutils"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("metadata-links")
FileUtils.mkdir_p(root)
original = File.join(root, "original.txt")
hard = File.join(root, "hard.txt")
symbolic = File.join(root, "symbolic.txt")
File.write(original, "ruby")
File.link(original, hard)
File.symlink("original.txt", symbolic)

A.truth(File.file?(original))
A.truth(File.directory?(root))
A.equal(File.stat(original).ino, File.stat(hard).ino)
A.truth(File.lstat(symbolic).symlink?)
A.equal("original.txt", File.readlink(symbolic))
A.equal(File.realpath(original), File.realpath(symbolic))

renamed = File.join(root, "renamed.txt")
File.rename(hard, renamed)
A.falsey(File.exist?(hard))
A.equal("ruby", File.read(renamed))

A.done
