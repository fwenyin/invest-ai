#!/usr/bin/env bash
# Build a CA bundle that Python (requests + curl_cffi/yfinance) will trust on a
# corporate laptop where a TLS-inspecting proxy (Zscaler/Netskope/etc.) re-signs
# HTTPS with a private root CA. macOS already trusts that root in the Keychain;
# this exports the Keychain roots + certifi's public roots into one bundle and
# prints the env vars to point Python at it. Run from the repo root.
#
#   bash scripts/setup_corp_ca.sh           # build + print exports
#   eval "$(bash scripts/setup_corp_ca.sh --export)"   # build + apply to shell
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

BUNDLE="$PWD/config/corp-ca-bundle.pem"
PY="$PWD/.venv/bin/python"

# 1) macOS system + corporate roots from the Keychain, then certifi's public roots.
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain >  "$BUNDLE"
security find-certificate -a -p /Library/Keychains/System.keychain                         >> "$BUNDLE"
cat "$("$PY" -c 'import certifi; print(certifi.where())')" >> "$BUNDLE"

LINES=(
  "export SSL_CERT_FILE=\"$BUNDLE\""
  "export REQUESTS_CA_BUNDLE=\"$BUNDLE\""
  "export CURL_CA_BUNDLE=\"$BUNDLE\""
)

if [ "${1:-}" = "--export" ]; then
  printf '%s\n' "${LINES[@]}"            # machine-readable for: eval "$(... --export)"
  exit 0
fi

echo "▸ Built CA bundle: $BUNDLE" >&2
echo "▸ Add these to ~/.zshrc (and launch Claude Code from that shell so the MCP server inherits them):" >&2
printf '\n'
printf '%s\n' "${LINES[@]}"
printf '\n'
echo "▸ Then verify:  .venv/bin/python tools/prices.py AAPL" >&2
