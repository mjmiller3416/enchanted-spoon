#!/usr/bin/env bash
# Create the Play upload keystore for com.enchantedspoon.app.
#
# Run this on the owner's machine. It is not part of CI. CI only decodes the
# base64 file into GitHub secret ANDROID_KEYSTORE_BASE64.
#
# The keystore, the base64 copy, and keystore.properties are written outside
# the repo (default: ~/enchanted-spoon-secrets/). Nothing here is committed.

set -euo pipefail

ALIAS="upload"
VALIDITY_DAYS=10000
KEY_ALG="RSA"
KEY_SIZE=4096
DNAME="CN=Enchanted Spoon Upload, OU=Android, O=Enchanted Spoon, C=US"
DEFAULT_DIR="${HOME:-}/enchanted-spoon-secrets"

usage() {
  cat <<'EOF'
Usage: scripts/android/generate-upload-keystore.sh [output-directory]

Creates an upload keystore (RSA 4096, 10,000-day validity, alias "upload")
outside the git repo. Passwords are read from the terminal and are not echoed.

Default output directory: ~/enchanted-spoon-secrets/
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 1
fi

if ! command -v keytool >/dev/null 2>&1; then
  echo "keytool is not on PATH. Install JDK 21 or newer and try again." >&2
  exit 1
fi

java_spec="$(
  java -XshowSettings:properties -version 2>&1 \
    | awk -F= '/java\.specification\.version/ { gsub(/ /, "", $2); print $2; exit }'
)"
java_major="${java_spec%%.*}"
if [[ -z "${java_major}" || "${java_major}" -lt 21 ]]; then
  echo "JDK 21 or newer is required (found specification '${java_spec:-unknown}')." >&2
  echo "Older keytool builds cannot take the password from the environment, which would put it on the command line." >&2
  exit 1
fi

OUT_DIR="${1:-${DEFAULT_DIR}}"
if [[ -z "${OUT_DIR}" ]]; then
  echo "HOME is not set and no output directory was given." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if git -C "${SCRIPT_DIR}" rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"
else
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
fi

OUT_DIR="$(realpath -m "${OUT_DIR}")"
REPO_ROOT="$(realpath "${REPO_ROOT}")"
case "${OUT_DIR}" in
  "${REPO_ROOT}"|"${REPO_ROOT}"/*)
    echo "Refusing to write the upload keystore inside the repo (${REPO_ROOT})." >&2
    echo "Choose a directory outside the repo. The default is ~/enchanted-spoon-secrets/." >&2
    exit 1
    ;;
esac

KEYSTORE_PATH="${OUT_DIR}/upload-keystore.jks"
BASE64_PATH="${OUT_DIR}/upload-keystore.jks.base64"
PROPS_PATH="${OUT_DIR}/keystore.properties"
CREATED=0

cleanup() {
  local status=$?
  unset STORE_PASS KEY_PASS
  if [[ "${status}" -ne 0 && "${CREATED}" -eq 1 ]]; then
    rm -f "${KEYSTORE_PATH}" "${BASE64_PATH}" "${PROPS_PATH}"
  fi
}
trap cleanup EXIT

if [[ -e "${KEYSTORE_PATH}" || -e "${BASE64_PATH}" || -e "${PROPS_PATH}" ]]; then
  echo "Refusing to overwrite existing upload-key material in ${OUT_DIR}." >&2
  echo "Move those files aside before generating a new upload key." >&2
  exit 1
fi

prompt_secret() {
  local __name="$1"
  local __prompt="$2"
  local __first=""
  local __second=""
  while true; do
    read -r -s -p "${__prompt}" __first
    printf '\n'
    read -r -s -p "Confirm: " __second
    printf '\n'
    if [[ -z "${__first}" ]]; then
      echo "Password cannot be empty." >&2
      continue
    fi
    if [[ "${__first}" != "${__second}" ]]; then
      echo "Those entries did not match. Try again." >&2
      continue
    fi
    printf -v "${__name}" '%s' "${__first}"
    unset __first __second
    return 0
  done
}

# Java properties escapes so a password can contain # ! = : or a backslash
# without being truncated when Gradle reads keystore.properties.
escape_property() {
  local input="$1"
  local output=""
  local char=""
  local code=0
  local i=0
  for ((i = 0; i < ${#input}; i++)); do
    char="${input:i:1}"
    case "${char}" in
      \\)
        # Two backslashes: Java properties treats `\\` as one backslash.
        output="${output}\\\\"
        ;;
      '#')
        output+='\#'
        ;;
      '!')
        output+='\!'
        ;;
      '=')
        output+='\='
        ;;
      ':')
        output+='\:'
        ;;
      *)
        printf -v code '%d' "'${char}"
        if (( code < 32 || code > 126 )); then
          if (( code > 65535 )); then
            echo "A password character is outside the range this properties file can store." >&2
            echo "Use ANDROID_KEYSTORE_PASSWORD and ANDROID_KEY_PASSWORD instead of keystore.properties." >&2
            exit 1
          fi
          printf -v output '%s\\u%04X' "${output}" "${code}"
        else
          output+="${char}"
        fi
        ;;
    esac
  done
  printf '%s' "${output}"
}

echo "Upload keystore for com.enchantedspoon.app"
echo "Alias: ${ALIAS}. Algorithm: ${KEY_ALG} ${KEY_SIZE}. Validity: ${VALIDITY_DAYS} days."
echo "Output directory: ${OUT_DIR}"
echo "Passwords are not printed and are not stored in the repo."
echo

prompt_secret STORE_PASS "Keystore password: "
prompt_secret KEY_PASS "Key password for alias '${ALIAS}': "
export STORE_PASS KEY_PASS

umask 077
mkdir -p "${OUT_DIR}"
chmod 700 "${OUT_DIR}"

CREATED=1
keytool -genkeypair \
  -alias "${ALIAS}" \
  -keyalg "${KEY_ALG}" \
  -keysize "${KEY_SIZE}" \
  -sigalg SHA256withRSA \
  -validity "${VALIDITY_DAYS}" \
  -keystore "${KEYSTORE_PATH}" \
  -storetype PKCS12 \
  -dname "${DNAME}" \
  -storepass:env STORE_PASS \
  -keypass:env KEY_PASS

chmod 600 "${KEYSTORE_PATH}"

echo
echo "Certificate fingerprints for alias ${ALIAS}:"
fingerprint_text="$(
  keytool -list -v \
    -alias "${ALIAS}" \
    -keystore "${KEYSTORE_PATH}" \
    -storepass:env STORE_PASS \
    | grep -E 'SHA1:|SHA256:|SHA-1:|SHA-256:' || true
)"
if [[ -z "${fingerprint_text}" ]]; then
  echo "keytool did not report SHA-1 or SHA-256 fingerprints." >&2
  exit 1
fi
printf '%s\n' "${fingerprint_text}"

if base64 --help 2>&1 | grep -q -- '--wrap'; then
  base64 --wrap=0 "${KEYSTORE_PATH}" > "${BASE64_PATH}"
elif base64 --help 2>&1 | grep -q -- '-w'; then
  base64 -w 0 "${KEYSTORE_PATH}" > "${BASE64_PATH}"
else
  base64 < "${KEYSTORE_PATH}" | tr -d '\n' > "${BASE64_PATH}"
fi
printf '\n' >> "${BASE64_PATH}"
chmod 600 "${BASE64_PATH}"

{
  printf 'storeFile=%s\n' "$(escape_property "${KEYSTORE_PATH}")"
  printf 'storePassword=%s\n' "$(escape_property "${STORE_PASS}")"
  printf 'keyAlias=%s\n' "$(escape_property "${ALIAS}")"
  printf 'keyPassword=%s\n' "$(escape_property "${KEY_PASS}")"
} > "${PROPS_PATH}"
chmod 600 "${PROPS_PATH}"

unset STORE_PASS KEY_PASS

cat <<EOF

Created (mode 600), outside the repo:
  Keystore:   ${KEYSTORE_PATH}
  Base64:     ${BASE64_PATH}
  Properties: ${PROPS_PATH}

The base64 file is the value of GitHub secret ANDROID_KEYSTORE_BASE64.
Copy the file contents into the secret. Do not commit the file.
The other secrets are ANDROID_KEYSTORE_PASSWORD, ANDROID_KEY_PASSWORD,
and ANDROID_KEY_ALIAS (use "${ALIAS}").

For a local bundleRelease, symlink the properties file into the Android
project. That path is gitignored:

  ln -sfn "${PROPS_PATH}" "${REPO_ROOT}/frontend/android/keystore.properties"

Backup — do this before you close this terminal:
  1. Save both passwords in a password manager (keystore password and key password).
  2. Keep an offline copy of the keystore file (encrypted disk or USB that is not
     this computer's only copy): ${KEYSTORE_PATH}
  3. Keep the base64 file with that offline copy. It is the same key, only encoded
     for CI. It does not belong in the repo, in chat, or in a screenshot.
  4. Play App Signing can reset a lost upload key, but that is a support process.
     Until it finishes you cannot ship an update. The password manager entry and
     the offline copy are the backup.

These files are gitignored (*.jks, *.keystore, *.jks.base64, keystore.properties)
in case a path inside the repo is used by mistake. Leave them outside the repo.
EOF
