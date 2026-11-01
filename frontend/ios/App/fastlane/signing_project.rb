# Removes the Capacitor template's project-level "iPhone Developer" identity
# from a pbxproj string. That setting conflicts with automatic signing on a
# GitHub runner, which has no Xcode account. Targets stay CODE_SIGN_STYLE =
# Automatic. The lane applies this to the CI checkout only.

module EnchantedSpoon
  module SigningProject
    IDENTITY_LINE = /^[ \t]*CODE_SIGN_IDENTITY = "iPhone Developer";\r?\n/.freeze

    def self.strip_template_identity(pbxproj_text)
      pbxproj_text.gsub(IDENTITY_LINE, "")
    end

    # CI checkout only. Sets the team and the version fastlane will archive,
    # and drops the Capacitor template identity that conflicts with automatic
    # signing. Build settings are not passed as xcodebuild arguments because
    # gym forwards xcargs to -exportArchive, which rejects them.
    def self.prepare(pbxproj_text, build_number:, marketing_version:, team_id:)
      build = Integer(build_number.to_s, 10)
      raise ArgumentError, "build number must be >= 1" if build < 1
      raise ArgumentError, "marketing version" unless marketing_version.match?(/\A\d+\.\d+(\.\d+)?\z/)
      raise ArgumentError, "team id" unless team_id.match?(/\A[A-Za-z0-9]{10}\z/)

      text = strip_template_identity(pbxproj_text)
      text = text.gsub(/CURRENT_PROJECT_VERSION = [^;]+;/, "CURRENT_PROJECT_VERSION = #{build};")
      text = text.gsub(/MARKETING_VERSION = [^;]+;/, "MARKETING_VERSION = #{marketing_version};")
      return text if text.include?("DEVELOPMENT_TEAM")

      text.gsub(/^([ \t]*)CODE_SIGN_STYLE = Automatic;/) do
        indent = Regexp.last_match(1)
        "#{indent}CODE_SIGN_STYLE = Automatic;\n#{indent}DEVELOPMENT_TEAM = #{team_id};"
      end
    end
  end
end

if $PROGRAM_NAME == __FILE__
  sample = <<~PBX
    \t\t\t\tCODE_SIGN_IDENTITY = "iPhone Developer";
    \t\t\t\tCODE_SIGN_STYLE = Automatic;
    \t\t\t\tCURRENT_PROJECT_VERSION = 1;
    \t\t\t\tMARKETING_VERSION = 1.0;
  PBX
  prepared = EnchantedSpoon::SigningProject.prepare(
    sample,
    build_number: 15,
    marketing_version: "1.2",
    team_id: "ABCDE12345",
  )
  raise "identity line remains" if prepared.include?("iPhone Developer")
  raise "automatic signing was removed" unless prepared.include?("CODE_SIGN_STYLE = Automatic;")
  raise "team missing" unless prepared.include?("DEVELOPMENT_TEAM = ABCDE12345;")
  raise "build" unless prepared.include?("CURRENT_PROJECT_VERSION = 15;")
  raise "version" unless prepared.include?("MARKETING_VERSION = 1.2;")
  puts "ok signing-project sample"
end
