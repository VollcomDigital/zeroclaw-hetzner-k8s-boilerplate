# Backend mount points

This repo does **not** vendor OpenClaw or NemoClaw sources.

| Directory   | Mounted in Compose as                         | Purpose                          |
|------------|------------------------------------------------|----------------------------------|
| `openclaw/` | `/workspace/backend/openclaw` (OpenClaw service) | Your OpenClaw tree (clone/symlink/copy here) |
| `nemoclaw/` | `/workspace/backend/nemoclaw` (NemoClaw service) | Your NemoClaw sandbox sources   |

Only `.keep` is committed so Git preserves empty directories. The stack can still start: containers use the published images plus whatever you place under these paths.
