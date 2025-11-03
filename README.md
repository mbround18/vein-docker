# VEIN Dedicated Server (Docker) 🎮

Run a VEIN dedicated game server in minutes with Docker - whether you're a complete beginner or a Docker veteran!

[![Docker Image](https://img.shields.io/badge/docker-mbround18%2Fvein--docker-blue)](https://hub.docker.com/r/mbround18/vein-docker)
[![License](https://img.shields.io/github/license/mbround18/vein-docker)](LICENSE)

## 📑 Table of Contents

- [TL;DR](#-tldr)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Setup](#quick-setup)
- [Compose Up](#-compose-up)
- [Compose Down](#-compose-down)
- [Maintenance](#-maintenance)
  - [Viewing Logs](#viewing-logs)
  - [Updating the Server](#updating-the-server)
  - [Backing Up Your Data](#backing-up-your-data)
  - [Saving Your World](#saving-your-world)
- [Configuration](#-configuration)
  - [Basic Settings](#basic-settings)
  - [Advanced Settings](#advanced-settings)
  - [Port Configuration](#port-configuration)
  - [Admin & Superadmin](#admin--superadmin)
  - [Server Ownership (Steam GSLT)](#server-ownership-steam-gslt)
- [Advanced Usage](#-advanced-usage)
  - [Kubernetes with Helm Charts](#kubernetes-with-helm-charts)
  - [Custom Docker Compose](#custom-docker-compose)
  - [INI Configuration](#ini-configuration)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🚀 TL;DR

**Got 60 seconds?** Here's everything you need:

```bash
# Clone or download this repository
git clone https://github.com/mbround18/vein-docker.git
cd vein-docker

# Copy and customize your settings
cp .env.example .env
# Edit .env with your preferred text editor

# Start your server
docker compose up -d

# Watch it come alive
docker compose logs -f
```

Your VEIN server is now running! 🎉
- **Data location**: `./data` directory
- **Default port**: 7777 (UDP)
- **Query port**: 27015 (UDP)

Players can connect to your server using your public IP address and port!

---

## 🎯 Getting Started

### Prerequisites

**New to Docker?** Don't worry! You just need:

- **Docker** installed on your machine ([Get Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** (included with Docker Desktop)
- A computer that can stay on while hosting (Windows, Mac, or Linux)
- A few minutes of your time

**Not sure if Docker is installed?** Run this command:
```bash
docker --version
docker compose version
```

If you see version numbers, you're good to go! If not, follow the [Docker installation guide](https://docs.docker.com/get-docker/).

### Quick Setup

1. **Get the files** - Choose one:
   
   Option A: Clone this repository (recommended)
   ```bash
   git clone https://github.com/mbround18/vein-docker.git
   cd vein-docker
   ```
   
   Option B: Download as ZIP from GitHub and extract it

2. **Configure your server**
   ```bash
   cp .env.example .env
   ```
   
   Open `.env` in your favorite text editor and customize:
   ```bash
   # Nano (Linux/Mac)
   nano .env
   
   # Notepad (Windows)
   notepad .env
   
   # Or use any text editor like VSCode, Sublime, etc.
   ```

3. **Customize these important settings:**
   ```env
   SERVER_NAME=My Awesome VEIN Server
   SERVER_PASSWORD=mysecretpassword
   MAX_PLAYERS=16
   ```

That's it! You're ready to launch. 🚀

---

## ⬆️ Compose Up

Starting your server is as simple as one command:

```bash
docker compose up -d
```

**What does this do?**
- `-d` runs it in "detached" mode (background)
- Downloads the VEIN server files automatically (first time only)
- Configures everything based on your `.env` file
- Starts your server and keeps it running

**First time setup?** The initial download might take 5-10 minutes depending on your internet speed. Grab a coffee! ☕

**Want to see what's happening?**
```bash
docker compose logs -f
```
Press `Ctrl+C` to stop viewing logs (your server keeps running).

---

## ⬇️ Compose Down

Need to stop your server? It's just as easy:

```bash
docker compose down
```

**What does this do?**
- Gracefully shuts down your server
- Attempts to save your world (if `SAVE_ON_SHUTDOWN=true` in `.env`)
- Stops and removes the container
- **Your data is safe** in the `./data` directory

**Pro tip:** Before shutting down, save your world manually for best results:
1. Connect to your server as an admin
2. Run the `Save` command
3. Wait a few seconds
4. Then run `docker compose down`

**Need to restart?**
```bash
docker compose restart
```

---

## 🔧 Maintenance

### Viewing Logs

Check what your server is doing:

```bash
# Follow logs in real-time (Ctrl+C to exit)
docker compose logs -f

# View last 100 lines
docker compose logs --tail 100

# Search logs for specific text
docker compose logs | grep "error"
```

### Updating the Server

Keep your server up-to-date with the latest VEIN version:

```bash
# Stop the server
docker compose down

# Pull the latest container image
docker compose pull

# Start with updates
docker compose up -d
```

The server will automatically update the game files on startup (if `UPDATE_ON_START=true`).

### Backing Up Your Data

Your world data is precious! Back it up regularly:

```bash
# Create a backup folder
mkdir -p backups

# Copy your data (while server is stopped)
docker compose down
cp -r ./data ./backups/backup-$(date +%Y%m%d-%H%M%S)
docker compose up -d
```

**Automated backups?** Consider setting up a cron job or scheduled task!

### Saving Your World

**Manual save (recommended before shutdown):**
1. Log in as superadmin (set `SUPERADMIN_STEAM_IDS` in `.env`)
2. Open the console in-game
3. Type: `Save`
4. Wait 5-10 seconds

**Automatic saves** are enabled by default (every 60 seconds). Configure in `.env`:
```env
AUTOSAVE_ENABLED=1
AUTOSAVE_INTERVAL=60
AUTOSAVE_MAX_QUANTITY=10
```

---

## ⚙️ Configuration

All configuration happens in the `.env` file. Here's everything you can customize:

### Basic Settings

These are the most common settings you'll want to adjust:

```env
# What players see in the server list
SERVER_NAME=My VEIN Server

# Password to join (leave empty for no password)
SERVER_PASSWORD=

# Admin console password
ADMIN_PASSWORD=

# Maximum players allowed
MAX_PLAYERS=16

# Server port (must match port forwarding)
SERVER_PORT=7777

# Query port (for server browser)
QUERY_PORT=27015
```

### Advanced Settings

For power users and specific needs:

```env
# Show server in public server list?
SERVER_PUBLIC=true

# Autosave configuration
AUTOSAVE_ENABLED=1
AUTOSAVE_INTERVAL=60
AUTOSAVE_MAX_QUANTITY=10

# Graceful shutdown with save
SAVE_ON_SHUTDOWN=true
SAVE_WAIT_SECONDS=5

# Network binding
BIND_ADDR=0.0.0.0
HEARTBEAT_INTERVAL=5.0
```

### Port Configuration

**Default ports** (UDP):
- `7777` - Main game server port
- `27015` - Query port (server browser)
- `27016` - Auxiliary port (optional)

**Important:** Don't forget to:
1. Forward these ports on your router
2. Allow them through your firewall
3. Match them in your `.env` file

**Changed the server port?** Update both:
```env
SERVER_PORT=8888
```
And in `compose.yml`:
```yaml
ports:
  - "8888:7777/udp"
```

### Admin & Superadmin

Grant yourself and friends admin powers:

```env
# Regular admins (comma-separated Steam64 IDs)
ADMIN_STEAM_IDS=76561198000000001,76561198000000002

# Superadmins (comma-separated Steam64 IDs)
SUPERADMIN_STEAM_IDS=76561198000000001
```

**How to find your Steam64 ID:**
1. Go to [steamid.io](https://steamid.io/)
2. Enter your Steam profile URL
3. Copy the `steamID64` number

**Multi-line format also works:**
```env
ADMIN_STEAM_IDS="76561198000000001
76561198000000002"
```

### Server Ownership (Steam GSLT)

Claim ownership of your server with a Steam Game Server Login Token:

1. **Generate a token**: Visit [Steam Game Server Account Management](https://steamcommunity.com/dev/managegameservers)
2. Use App ID: `1857950`
3. **Add to `.env`:**
   ```env
   STEAM_GSLT=YOURTOKENHERE
   ```

⚠️ **Never share or commit your GSLT token!** It's like a password.

**Benefits:**
- Claim server ownership
- Better server listing
- Track server stats

---

## 🚀 Advanced Usage

### Kubernetes with Helm Charts

Running a production environment? Deploy on Kubernetes!

**Helm repository:** https://github.com/mbround18/helm-charts

The charts are published via GitHub Pages. Use the `vein` chart:

```bash
# Add the Helm repository
helm repo add mbround18 https://mbround18.github.io/helm-charts/
helm repo update

# Install the VEIN server
helm install vein-server mbround18/vein

# Or with custom values
helm install vein-server mbround18/vein -f my-values.yaml
```

**Example `my-values.yaml`:**
```yaml
env:
  SERVER_NAME: "My K8s VEIN Server"
  MAX_PLAYERS: "32"
  SERVER_PUBLIC: "true"

persistence:
  enabled: true
  size: 20Gi

resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

**Check the chart documentation** in the Helm repository for all available options!

### Custom Docker Compose

Want to start from scratch? Here's a minimal `docker-compose.yml`:

```yaml
services:
  vein:
    image: mbround18/vein-docker:latest
    container_name: vein
    restart: unless-stopped
    env_file:
      - .env
    environment:
      SERVER_PORT: "${SERVER_PORT:-7777}"
      QUERY_PORT: "${QUERY_PORT:-27015}"
    ports:
      - "${SERVER_PORT:-7777}:7777/udp"
      - "${QUERY_PORT:-27015}:27015/udp"
      - "27016:27016/udp"
    volumes:
      - ./data:/home/steam/vein
```

Then create your `.env` file and run:
```bash
docker compose up -d
```

### INI Configuration

The container automatically manages `Game.ini` settings. Advanced users can add custom overrides:

```env
INI_ENABLE=true
INI_EXTRA_OVERRIDES=|
  Game.ini:/script/engine.gamesession:MaxPlayers=32
  Game.ini:/script/vein.veingamesession:BindAddr=0.0.0.0
```

**Format:** `filename:section:key=value`

**Sections managed by default:**
- `[/script/engine.gamesession]` - MaxPlayers
- `[/script/vein.veingamesession]` - bPublic, ServerName, BindAddr, Password, AdminSteamIDs, SuperAdminSteamIDs

---

## 🔍 Troubleshooting

### Server won't start

**Check logs first:**
```bash
docker compose logs
```

**Common issues:**

1. **"Could not determine server start command"**
   - The game files didn't download properly
   - Solution: `docker compose down && rm -rf ./data && docker compose up -d`

2. **Port already in use**
   - Another application is using port 7777
   - Solution: Change `SERVER_PORT` in `.env` or stop the conflicting application

3. **Permission errors**
   - The container can't write to `./data`
   - Solution (Linux/Mac): `chmod -R 755 ./data`

### Players can't connect

1. **Check your firewall** - Allow UDP ports 7777 and 27015
2. **Port forwarding** - Forward these ports on your router to your server's local IP
3. **Verify ports match** - `.env` settings must match your `compose.yml` and router config
4. **Test locally first** - Can you connect using `localhost:7777`?

### Server not appearing in browser

- Set `SERVER_PUBLIC=true` in `.env`
- Ensure `QUERY_PORT` (27015) is open and forwarded
- Consider getting a Steam GSLT token

### Save files not working

- Set yourself as superadmin: `SUPERADMIN_STEAM_IDS=your_steam64_id`
- Manually save before shutting down: Run `Save` command in-game
- Enable automatic shutdown saves: `SAVE_ON_SHUTDOWN=true`

### Need more help?

- Check existing issues: [GitHub Issues](https://github.com/mbround18/vein-docker/issues)
- Open a new issue with:
  - Your `.env` settings (remove passwords!)
  - Output from `docker compose logs`
  - What you've already tried

---

## 🤝 Contributing

We love contributions! Whether you're fixing bugs, improving docs, or adding features - you're welcome here.

**Ways to contribute:**
- 🐛 Report bugs via [GitHub Issues](https://github.com/mbround18/vein-docker/issues)
- 📝 Improve documentation
- 💻 Submit pull requests
- ⭐ Star the project
- 📢 Share with friends

**Development setup:**
```bash
git clone https://github.com/mbround18/vein-docker.git
cd vein-docker
cp .env.example .env
docker compose up --build -d
```

**Read more:** See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 💙 Thank You!

Thank you for using this container! We hope it makes hosting your VEIN server easy and enjoyable.

**Having a great experience?** Consider:
- ⭐ Starring the repository
- 🐦 Sharing with your community
- 💬 Providing feedback

**Running into issues?** Don't hesitate to open an issue. We're here to help!

Happy gaming! 🎮

---

**Project maintained by:** [@mbround18](https://github.com/mbround18)  
**License:** See [LICENSE](LICENSE)  
**Docker Hub:** [mbround18/vein-docker](https://hub.docker.com/r/mbround18/vein-docker)
