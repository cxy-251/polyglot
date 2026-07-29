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
A.equal(4, path.stat.size)

link = Pathname(root).join("link.txt")
File.symlink(Pathname("nested/value.txt"), link)
A.truth(link.symlink?)
A.equal("nested/value.txt", link.readlink.to_s)
A.equal(path.realpath, link.realpath)
A.truth(File.identical?(path, link))
A.falsey(link.lstat.ftype == link.stat.ftype)

A.done
