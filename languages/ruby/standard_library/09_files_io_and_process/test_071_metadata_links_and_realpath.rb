# frozen_string_literal: true
# polyglot-covers: ruby.stdlib.metadata-links-and-realpath

require "assertions"
require "fileutils"
require "helpers"

A = PolyglotAssertions
H = PolyglotRubyHelpers

root = H.temporary_path("metadata")
FileUtils.mkdir_p(root)
target = File.join(root, "target.txt")
link = File.join(root, "link.txt")
File.write(target, "data")
File.symlink("target.txt", link)

A.truth(File.file?(link))
A.truth(File.symlink?(link))
A.equal("target.txt", File.readlink(link))
A.equal(File.realpath(target), File.realpath(link))
A.equal(4, File.stat(target).size)
A.falsey(File.lstat(link).ftype == File.stat(link).ftype)
A.truth(File.identical?(target, link))

A.done
