# Frozen build-number rule for the TestFlight lane.
# Loaded by Fastfile. Run this file directly to check the rule:
#   ruby frontend/ios/App/fastlane/build_number.rb

module EnchantedSpoon
  module IosBuildNumber
    # Next CFBundleVersion. Apple rejects an upload that reuses a build
    # number for the same marketing version, so the TestFlight value wins
    # when it is ahead. GITHUB_RUN_NUMBER wins when it is ahead, which
    # covers a fresh app with no TestFlight builds and a run number that
    # has already moved past 1.
    def self.choose(latest_testflight_build:, github_run_number:)
      from_store = Integer(latest_testflight_build.to_s, 10) + 1
      from_run = Integer(github_run_number.to_s, 10)
      raise ArgumentError, "TestFlight build number must be >= 0" if from_store < 1
      raise ArgumentError, "GITHUB_RUN_NUMBER must be >= 1" if from_run < 1

      [from_store, from_run].max
    end
  end
end

if $PROGRAM_NAME == __FILE__
  cases = [
    [{ latest_testflight_build: 0, github_run_number: 1 }, 1],
    [{ latest_testflight_build: 0, github_run_number: 15 }, 15],
    [{ latest_testflight_build: 12, github_run_number: 3 }, 13],
    [{ latest_testflight_build: "12", github_run_number: "100" }, 100],
    [{ latest_testflight_build: 41, github_run_number: 42 }, 42],
    [{ latest_testflight_build: 42, github_run_number: 42 }, 43],
  ]
  cases.each do |kwargs, expected|
    actual = EnchantedSpoon::IosBuildNumber.choose(**kwargs)
    raise "choose(#{kwargs.inspect}) = #{actual}, expected #{expected}" unless actual == expected
  end
  puts "ok #{cases.length} build-number cases"
end
