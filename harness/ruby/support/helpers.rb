# frozen_string_literal: true
# Harness process and temporary-resource support; this file is not a course unit.

require "fileutils"
require "open3"
require "rbconfig"

module PolyglotRubyHelpers
  module_function

  def temporary_path(name)
    root = ENV.fetch("POLYGLOT_RUBY_TEST_TMP")
    path = File.join(root, name)
    FileUtils.rm_rf(path)
    path
  end

  def ruby_command(*arguments, stdin_data: "", environment: {})
    command = [
      RbConfig.ruby,
      "--disable-did_you_mean",
      "--disable-error_highlight",
      *arguments
    ]
    stdout, stderr, status = Open3.capture3(environment, *command, stdin_data:)
    [stdout, stderr, status]
  end

  def extension_directory
    ENV.fetch("POLYGLOT_RUBY_EXTENSION_DIR")
  end

  def isolated_gem_environment
    {
      "HOME" => ENV.fetch("HOME"),
      "GEM_HOME" => ENV.fetch("POLYGLOT_RUBY_GEM_HOME"),
      "GEM_PATH" => ENV.fetch("GEM_PATH"),
      "GEMRC" => "/dev/null",
      "BUNDLE_USER_HOME" => ENV.fetch("POLYGLOT_RUBY_BUNDLE_HOME"),
      "BUNDLE_DISABLE_VERSION_CHECK" => "true",
      "BUNDLE_SILENCE_ROOT_WARNING" => "true",
      "BUNDLE_ALLOW_OFFLINE_INSTALL" => "true"
    }
  end
end
