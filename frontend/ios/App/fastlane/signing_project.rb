# Removes the Capacitor template's project-level "iPhone Developer" identity
# from a pbxproj string. That setting conflicts with automatic signing on a
# GitHub runner, which has no Xcode account. Targets stay CODE_SIGN_STYLE =
# Automatic. The lane applies this to the CI checkout only.

module EnchantedSpoon
  # Mitchell's individual Apple Developer team. Not a secret.
  # APPLE_TEAM_ID (GitHub Actions secret) overrides this when it is set.
  DEFAULT_APPLE_TEAM_ID = "FVTC8T7SB2".freeze

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
      apply_development_team(text, team_id)
    end

    # A committed DEVELOPMENT_TEAM is the local default. The lane's team_id
    # still wins, including when APPLE_TEAM_ID overrides the default.
    # Automatic targets with no team (the share extension) get one line.
    # A team that is not the next line after CODE_SIGN_STYLE is left where
    # it is, so the App target does not gain a second DEVELOPMENT_TEAM.
    def self.apply_development_team(text, team_id)
      text = text.gsub(/DEVELOPMENT_TEAM = [^;]+;/, "DEVELOPMENT_TEAM = #{team_id};")
      text.gsub(/^([ \t]*)CODE_SIGN_STYLE = Automatic;(\r?\n)/) do
        indent = Regexp.last_match(1)
        newline = Regexp.last_match(2)
        line = "#{indent}CODE_SIGN_STYLE = Automatic;#{newline}"
        next line if settings_block_has_team?(Regexp.last_match)

        "#{line}#{indent}DEVELOPMENT_TEAM = #{team_id};#{newline}"
      end
    end

    def self.settings_block_has_team?(match)
      pre = match.pre_match
      post = match.post_match
      start = pre.rindex("buildSettings = {")
      block_pre = start ? pre[start..] : pre
      close = post.index(/\n[ \t]*\};/)
      block_post = close ? post[0..close] : post
      "#{block_pre}#{block_post}".include?("DEVELOPMENT_TEAM")
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

  already = <<~PBX
    \t\t\tbuildSettings = {
    \t\t\t\tCODE_SIGN_STYLE = Automatic;
    \t\t\t\tCURRENT_PROJECT_VERSION = 1;
    \t\t\t\tDEVELOPMENT_TEAM = FVTC8T7SB2;
    \t\t\t};
    \t\t\tbuildSettings = {
    \t\t\t\tCODE_SIGN_STYLE = Automatic;
    \t\t\t\tCURRENT_PROJECT_VERSION = 1;
    \t\t\t};
  PBX
  overridden = EnchantedSpoon::SigningProject.prepare(
    already,
    build_number: 2,
    marketing_version: "1.0",
    team_id: "ABCDE12345",
  )
  raise "committed team was kept" if overridden.include?("FVTC8T7SB2")
  raise "override missing" unless overridden.scan("DEVELOPMENT_TEAM = ABCDE12345;").length == 2
  raise "duplicate team on a target" if overridden.scan("DEVELOPMENT_TEAM").length != 2
  raise "default team id" unless EnchantedSpoon::DEFAULT_APPLE_TEAM_ID == "FVTC8T7SB2"
  puts "ok signing-project sample"
end
