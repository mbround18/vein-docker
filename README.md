# VEIN Dedicated Server (Docker)

Run a VEIN dedicated server in minutes with Docker.

Status: Working. The container auto-detects `VeinServer.sh`, supports env-based config, and writes settings into `Game.ini`.

## Quick start

1) Copy the sample dotenv and edit values

```sh
cp .env.example .env
```

1) Start the server

```sh
docker compose up -d
```

1) Watch logs

```sh
docker compose logs -f
```

Data is stored in `./data` (mounted to `/home/steam/vein`).

## Copy‑paste docker‑compose.yml

If you prefer starting from an empty folder, create a `docker-compose.yml` like this and place a `.env` next to it (see `.env.example` below):

```yaml
services:
  vein:
    image: mbround18/vein-docker:latest
    container_name: vein
    restart: unless-stopped
    env_file:
      - .env
    environment:
      # Defaults come from .env; these two control published ports:
      SERVER_PORT: "${SERVER_PORT:-7777}"
      QUERY_PORT: "${QUERY_PORT:-27015}"
    ports:
      - "${SERVER_PORT:-7777}:7777/udp"
      - "${QUERY_PORT:-27015}:27015/udp"
      - "27016:27016/udp"  # optional/aux
    volumes:
      - ./data:/home/steam/vein
```

Then run:

```sh
cp .env.example .env
docker compose up -d
```

## Configure via .env

Most users only need to set a few values in `.env`:

- SERVER_NAME — shown to players
- SERVER_PASSWORD — required to join (optional)
- ADMIN_PASSWORD — admin console password (optional)
- MAX_PLAYERS — default 16
- SERVER_PORT — default 7777 (UDP)
- QUERY_PORT — default 27015 (UDP)

Advanced (optional):

- SERVER_PUBLIC — true/false
- ADMIN_STEAM_IDS — comma/newline list of Steam64 IDs
- SUPERADMIN_STEAM_IDS — comma/newline list of Steam64 IDs
- STEAM_GSLT — Game Server Login Token to claim ownership
- AUTOSAVE_ENABLED — 1 (enabled) or 0 (disabled), default 1
- AUTOSAVE_INTERVAL — seconds between autosaves, default 60
- AUTOSAVE_MAX_QUANTITY — maximum number of autosave files to keep, default 10
- CODE_8_MITIGATION — true/false to enable automatic recovery from SteamCMD error code 8 (default true)
- INI_ENABLE — true/false to write settings into Game.ini (default true)
- INI_EXTRA_OVERRIDES — extra lines like `Game.ini:/script/vein.veingamesession:BindAddr=0.0.0.0`
- EXTRA_ARGS — extra flags passed to `VeinServer.sh`

The container will:

- Install/update the server with SteamCMD into `/home/steam/vein`
- Prefer running `VeinServer.sh`
- Apply your settings as launch args
- Write the same values into `Game.ini` (if `INI_ENABLE=true`)

### INI settings written

`Game.ini` sections and keys managed by the container:

- [/script/engine.gamesession]
  - MaxPlayers
- [/script/vein.veingamesession]
  - bPublic
  - ServerName
  - BindAddr
  - HeartbeatInterval
  - Password
  - AdminSteamIDs (one per line)
  - SuperAdminSteamIDs (one per line)

IDs provided in `ADMIN_STEAM_IDS` and `SUPERADMIN_STEAM_IDS` are normalized from comma or newline lists into one-per-line entries.

### Claim server ownership (Steam GSLT)

1) Generate a token at: <https://steamcommunity.com/dev/managegameservers> (App ID `1857950`)

2) Put it in `.env` as `STEAM_GSLT=...`

On launch, the server is started with `+sv_setsteamaccount <token>`. Never commit your token.

## Ports

Default mappings (configure via `.env`):

- 7777/udp — server port (SERVER_PORT)
- 27015/udp — query port (QUERY_PORT)
- 27016/udp — optional/aux; remove if unused

Open these ports on your firewall and router as needed.

## Known issues

- Save on shutdown: We’re actively working on a save-on-exit bug. Until this is fixed:
  - Add yourself as superadmin by setting `SUPERADMIN_STEAM_IDS=<your_steam64_id>` in `.env`.
  - In-game as superadmin (or via the server console), run the command: `Save`
  - Wait a few seconds, then stop the container.
  - Note: The container can also attempt a best‑effort save on stop when `SAVE_ON_SHUTDOWN=true`, but please still prefer an explicit `Save` command before shutdown.

## SteamCMD Error Code 8 Mitigation

SteamCMD sometimes fails with exit code 8 due to corrupted files or failed delta updates. When `CODE_8_MITIGATION=true` (default), the container automatically recovers by:

1. Backing up your saves from `/home/steam/vein/Vein/Saved` to `$HOME/.backup`
2. Deleting the entire install directory
3. Performing a clean installation
4. Restoring your saves from backup

This ensures your game progress is preserved even when SteamCMD encounters update issues. Your saves are never at risk.

## Troubleshooting

- Could not determine server start command
  - Ensure `VeinServer.sh` exists under `/home/steam/vein` after install
  - Otherwise set `START_COMMAND` in `.env`
- Ports unreachable
  - Verify firewall/NAT and that published ports match `.env`
- INI not updating
  - Ensure `INI_ENABLE=true` and the container can write to `./data`
- SteamCMD error code 8 on updates
  - This is automatically handled when `CODE_8_MITIGATION=true` (default)
  - Your saves are backed up and restored automatically
  - Check logs for "Code 8 mitigation" messages

---

Looking to build or develop locally? See CONTRIBUTING.md.
