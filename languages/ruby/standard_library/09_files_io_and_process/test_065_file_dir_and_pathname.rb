# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.file-dir-and-pathname

require "assertions"
require "fileutils"
require "helpers"
require "pathname"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("file-tree")
FileUtils.mkdir_p(File.join(root, "nested"))
path = Pathname(root).join("nested", "..", "nested", "value.txt").cleanpath
path.write("ruby")

A.truth(path.file?)
A.equal("ruby", path.read)
A.equal("value.txt", path.basename.to_s)
A.equal(["value.txt"], Dir.children(path.dirname).sort)
A.truth(Pathname(root).directory?)
A.equal(path.to_s, File.join(root, "nested", "value.txt"))

A.done
