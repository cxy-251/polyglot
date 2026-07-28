# frozen_string_literal: true

require "mkmf"

abort "ruby.h is required" unless have_header("ruby.h")
abort "ruby/thread.h is required" unless have_header("ruby/thread.h")

$CFLAGS = [
  $CFLAGS,
  "-std=c11",
  "-Wall",
  "-Wextra",
  "-Werror"
].join(" ")

create_makefile("polyglot_native")
