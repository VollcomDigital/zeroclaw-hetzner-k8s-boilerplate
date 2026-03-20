# 1Password Connect credentials (local)

`docker-compose.local.yml` bind-mounts `secrets/1password-credentials.json` into the Connect containers.

1. Install the 1Password CLI (`op`) and authenticate to your account.
2. Run the Connect provisioning flow per [1Password Connect — get started](https://developer.1password.com/docs/connect/get-started/).
3. Place the generated credentials JSON in `secrets/1password-credentials.json` (gitignored).

`make dev-mac` / `make dev-windows` copies `1password-credentials.json.example` to that path if it is missing so local `docker compose` can start without file errors. Replace it with a valid provisioning artifact before relying on the MCP secret tools.
