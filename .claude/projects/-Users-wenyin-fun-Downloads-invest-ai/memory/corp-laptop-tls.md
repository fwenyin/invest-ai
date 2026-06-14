---
name: corp-laptop-tls
description: User runs invest-ai on a corporate laptop whose TLS-inspection proxy breaks Python HTTPS (SSL cert errors)
metadata:
  type: project
---

The user runs this project on a **company-issued macOS laptop** (host `DBSG-JXCX90TYYF`)
behind a corporate **TLS-inspecting proxy**. It re-signs HTTPS with a private root CA that
macOS Keychain trusts but Python's `certifi` does not, so tools fail with
`SSL: CERTIFICATE_VERIFY_FAILED / unable to get local issuer certificate`. Affects
`requests`-based tools (Finnhub, Reddit) **and** `curl_cffi`/yfinance (prices, options,
financials). GitHub/Yahoo pass through un-inspected, so `trump.py` (GitHub fallback) still worked.

**Fix (confirmed working):** build a combined CA bundle from Keychain roots + certifi and point
all three TLS stacks at it via `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` / `CURL_CA_BUNDLE`.
Helper: `scripts/setup_corp_ca.sh` (writes `config/corp-ca-bundle.pem`, gitignored). For the MCP
server + `/premarket` to inherit it, the exports must be in `~/.zshrc` and Claude Code launched
from that shell; `launchd` scheduled jobs need the vars in the plist (not yet wired into
`gen_schedule.py`). Never use `verify=False`.

**Why:** corporate proxy, not a code/.env bug. **How to apply:** if the user reports SSL cert
errors, point them at this fix rather than re-debugging. Also flag: running a personal trading
desk on a monitored work laptop is a policy/privacy consideration. Related: [[trump-source-stale]].
