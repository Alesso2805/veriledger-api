#!/bin/sh
# Checks a running VeriLedger behind Caddy (VLA-27): the API under /api, the webapp at /, over HTTPS.
# Usage: deploy/verify.sh https://<domain>. With ADMIN_EMAIL and ADMIN_PASSWORD set, it also signs in.
# A rehearsal on localhost trusts Caddy's own CA through CURL_CA_BUNDLE (docs/runbooks/deploy.md).
set -eu

base="${1:?usage: deploy/verify.sh https://<domain>}"

fail() {
  echo "verify: $*" >&2
  exit 1
}

# Caddy may still be fetching its certificate, and the API waiting for the database
for _ in $(seq 1 60); do
  curl -fsS "$base/api/health" >/dev/null 2>&1 && break
  sleep 2
done

health="$(curl -fsS "$base/api/health")" || fail "/api/health does not answer 200"
echo "$health" | grep -q '"database":"ok"' || fail "/api/health does not report the database: $health"
curl -fsS "$base/api/docs" | grep -q '/api/openapi.json' || fail "/api/docs does not read /api/openapi.json"
curl -fsS "$base/api/openapi.json" >/dev/null || fail "/api/openapi.json does not answer"

curl -fsS "$base/" | grep -q '<div id="root">' || fail "/ does not serve the webapp"
curl -fsS "$base/wallet" | grep -q '<div id="root">' || fail "the deep link /wallet does not serve the webapp"
curl -fsS "$base/config.json" | grep -q '"apiBaseUrl": "/api"' || fail "/config.json does not point at /api"

if curl -fsS -D - -o /dev/null "$base/api/health" | grep -qi '^server:'; then fail "the Server header is sent"; fi

if [ -n "${ADMIN_EMAIL:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
  curl -fsS --data-urlencode "username=$ADMIN_EMAIL" --data-urlencode "password=$ADMIN_PASSWORD" \
    "$base/api/auth/login" | grep -q '"access_token"' || fail "the admin cannot sign in"
fi

echo "verify: ok ($base)"
