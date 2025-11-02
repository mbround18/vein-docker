# Contributing

Thanks for improving the VEIN Docker project! This guide is for contributors and maintainers.

## Prerequisites

- Docker and Docker Compose
- A Linux host is recommended (the image targets linux/amd64)

## Local development workflow

- Build and run with Compose using the local Dockerfile:

```sh
# Build on first run or when you change Dockerfile/entrypoint
docker compose up --build -d

# Tail logs
docker compose logs -f

# Stop
docker compose down
```

- Edit `scripts/entrypoint.sh` or other files and re-run with `--build` to apply changes.

- Data persists under `./data` (bind-mounted to `/home/steam/vein`). Remove it to reset the install:

```sh
docker compose down
rm -rf ./data
```

## Environment variables

The container reads configuration from environment variables (usually via `.env`). See `.env.example` for a complete list and defaults.

Key variables:

- SERVER_NAME, SERVER_PASSWORD, ADMIN_PASSWORD
- SERVER_PORT, QUERY_PORT, MAX_PLAYERS
- SERVER_PUBLIC, ADMIN_STEAM_IDS, SUPERADMIN_STEAM_IDS
- STEAM_GSLT
- INI_ENABLE, INI_EXTRA_OVERRIDES, EXTRA_ARGS, START_COMMAND

## Compose tips

- The compose file publishes UDP ports; confirm they match your `.env` values.
- `env_file: [.env]` is used so most values live in `.env` instead of the compose file.
- If you don’t want to build locally and prefer a prebuilt image, set the service to `image: mbround18/vein-docker:latest` and remove the `build:` block.

## Coding standards

- Shell: POSIX-ish with Bash; set `set -Eeuo pipefail`
- Avoid leaking secrets in logs; mask passwords when echoing commands
- Keep INI writes idempotent and predictable (no spaces around `=`)
- Prefer small, focused changes

## Testing changes

- Verify the entrypoint can:
  - Install/update via SteamCMD
  - Detect and launch `VeinServer.sh`
  - Apply CLI args derived from env
  - Write expected keys to `Game.ini`

## Releasing

- Update `.env.example` and `README.md` when adding new env vars or behavior.
- Keep the README user-focused; developer details belong here.
