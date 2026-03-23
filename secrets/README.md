# 1Password Connect credentials (local)

`docker-compose.local.yml` bind-mounts `secrets/1password-credentials.json` into the Connect containers.

1. Install the 1Password CLI (`op`) and authenticate to your account.
2. Provision Connect per [Get started with a 1Password Connect server](https://developer.1password.com/docs/connect/get-started/) (dashboard wizard or [`op connect server create`](https://developer.1password.com/docs/cli/reference/management-commands/connect/#connect-server-create)).
3. Place the generated `1password-credentials.json` here (gitignored). Create a Connect access token with [`op connect token create`](https://developer.1password.com/docs/cli/reference/management-commands/connect/#connect-token-create) and set `OP_CONNECT_TOKEN` in `.env.local`.

`make dev-mac` / `make dev-windows` / `scripts/local-dev.ps1` copy `1password-credentials.json.example` if the file is missing so Compose can start; replace it with a real provisioning artifact before relying on MCP secret tools.

## Connect cannot use Employee / Personal / Private / default Shared vaults

If the CLI returns:

`Granting Connect access to a Personal, Private, or Employee vault is not currently supported`

that is expected: Connect **must not** be granted those built-in vaults (including **Employee**). You need a **separate vault created for automation** (team-created shared vault), then grant access to that vault. See [Create a vault](https://support.1password.com/create-share-vaults/) and the requirements in the [Connect get-started](https://developer.1password.com/docs/connect/get-started/#requirements) doc.

You can create the server without vaults (`op connect server create nemoclaw`) and later run [`op connect vault grant`](https://developer.1password.com/docs/cli/reference/management-commands/connect/#connect-vault-grant) for an allowed vault name or ID.

## `unable to find vault with ID '…'`

`--vaults` expects vault **IDs** (UUIDs from your account), not arbitrary labels. The CLI error means nothing matched that string as a vault identifier.

1. Create the vault in 1Password first if it does not exist ([Create a vault](https://support.1password.com/create-share-vaults/))—must be a type Connect allowed (not Personal / Private / Employee / default Shared).
2. Run `op vault list` and copy the **id** column for that vault.
3. Pass that UUID: `op connect server create nemoclaw --vaults "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"` (repeat `--vaults` for multiple vaults).

If you are unsure of the name, use the ID only; names alone are not guaranteed to resolve the way the CLI error suggests.
