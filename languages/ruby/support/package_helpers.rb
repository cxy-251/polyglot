# frozen_string_literal: true

require "fileutils"
require "open3"
require "rbconfig"
require "rubygems"
require "helpers"

module PolyglotRubyPackages
  module_function

  def fixture_source
    File.expand_path("../gem_fixture/polyglot_ruby_fixture", __dir__)
  end

  def prepare_fixture(label)
    destination = PolyglotRubyHelpers.temporary_path(label)
    FileUtils.cp_r(fixture_source, destination)
    destination
  end

  def tool_path(name)
    File.join(RbConfig::CONFIG.fetch("bindir"), name)
  end

  def run_tool(name, *arguments, chdir:, environment: {})
    command_environment = PolyglotRubyHelpers.isolated_gem_environment.merge(environment)
    Open3.capture3(
      command_environment,
      tool_path(name),
      *arguments,
      chdir:
    )
  end

  def build_gem(label)
    source = prepare_fixture(label)
    stdout, stderr, status = run_tool(
      "gem",
      "build",
      "polyglot_ruby_fixture.gemspec",
      chdir: source
    )
    raise "gem build failed: #{stdout}\n#{stderr}" unless status.success?

    [source, Dir.glob(File.join(source, "*.gem")).fetch(0)]
  end

  def write_bundler_app(label)
    application = PolyglotRubyHelpers.temporary_path(label)
    gem_path = File.join(application, "polyglot_ruby_fixture")
    FileUtils.mkdir_p(application)
    FileUtils.cp_r(fixture_source, gem_path)
    File.write(
      File.join(application, "Gemfile"),
      "gem \"polyglot_ruby_fixture\", path: \"./polyglot_ruby_fixture\"\n"
    )
    application
  end

  def bundler_environment(application)
    {
      "BUNDLE_GEMFILE" => File.join(application, "Gemfile"),
      "BUNDLE_APP_CONFIG" => File.join(application, ".bundle"),
      "BUNDLE_PATH" => File.join(application, "bundle"),
      "BUNDLE_DEPLOYMENT" => "false"
    }
  end
end
