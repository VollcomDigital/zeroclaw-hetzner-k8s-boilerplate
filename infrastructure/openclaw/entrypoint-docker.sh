#!/bin/sh
set -eu
# Persisted /data/.openclaw/openclaw.json may contain gateway.bind=loopback from older runs.
# configure.js deep-merges that file on top of OPENCLAW_CUSTOM_CONFIG and wins over OPENCLAW_GATEWAY_BIND.
# Remove bind so the next configure pass restores lan/0.0.0.0 from custom JSON + env (Docker + Traefik need this).
CONFIG="/data/.openclaw/openclaw.json"
if [ -f "$CONFIG" ]; then
  node <<'NODE' || true
const fs = require("fs");
const p = "/data/.openclaw/openclaw.json";
try {
  const raw = fs.readFileSync(p, "utf8");
  const c = JSON.parse(raw);
  if (c.gateway && Object.prototype.hasOwnProperty.call(c.gateway, "bind")) {
    delete c.gateway.bind;
    fs.writeFileSync(p, JSON.stringify(c, null, 2));
  }
} catch {
  /* ignore */
}
NODE
fi
exec /app/scripts/entrypoint.sh "$@"
