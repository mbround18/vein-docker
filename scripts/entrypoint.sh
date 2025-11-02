#!/usr/bin/env bash
set -Eeuo pipefail

echo "──────────────────────────────────────────────────────────"
echo "🚀 VEIN Docker - $(date)"
echo "──────────────────────────────────────────────────────────"

# System Info
echo "🔹 Hostname: $(hostname)"
echo "🔹 Kernel: $(uname -r)"
echo "🔹 OS: $(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')"
echo "🔹 CPU: $(lscpu | grep 'Model name' | cut -d: -f2 | sed 's/^ *//')"
echo "🔹 Memory: $(free -h | awk '/^Mem:/ {print $2}')"
echo "🔹 Disk Space: $(df -h / | awk 'NR==2 {print $4}')"
echo "──────────────────────────────────────────────────────────"

echo "👤 Running as user: $(whoami) (UID: $(id -u), GID: $(id -g))"
echo "👥 Groups: $(id -Gn)"

INSTALL_DIR="${INSTALL_DIR:-/home/steam/vein}"
APP_ID="${APP_ID:-2131400}"
STEAM_USERNAME="${STEAM_USERNAME:-anonymous}"
STEAM_PASSWORD="${STEAM_PASSWORD:-}"
VALIDATE_FLAG="${VALIDATE:-false}"
UPDATE_ON_START="${UPDATE_ON_START:-true}"
START_COMMAND="${START_COMMAND:-}" # Allow overriding when the server binary/args are known
INI_ENABLE="${INI_ENABLE:-true}"
SERVER_PUBLIC="${SERVER_PUBLIC:-true}"
BIND_ADDR="${BIND_ADDR:-0.0.0.0}"
HEARTBEAT_INTERVAL="${HEARTBEAT_INTERVAL:-5.0}"
ADMIN_STEAM_IDS="${ADMIN_STEAM_IDS:-}"
SUPERADMIN_STEAM_IDS="${SUPERADMIN_STEAM_IDS:-}"
SAVE_ON_SHUTDOWN="${SAVE_ON_SHUTDOWN:-true}"
SAVE_WAIT_SECONDS="${SAVE_WAIT_SECONDS:-5}"

# Helper: update INI values using crudini
set_ini_kv() {
  local file="$1"; shift
  local section="$1"; shift
  local key="$1"; shift
  local value="$1"; shift || true
  mkdir -p "$(dirname "$file")"
  touch "$file"
  # Strip surrounding brackets from section if present
  local sec_clean="${section#[}"; sec_clean="${sec_clean%]}"
  crudini --set "$file" "$sec_clean" "$key" "$value"
}

# Helper: ensure section exists
ensure_section() {
  local file="$1" section="$2"
  crudini --set "$file" "${section#[}" "__ensure" "__ensure" 2>/dev/null || true
  crudini --del "$file" "${section#[}" "__ensure" 2>/dev/null || true
}

# Helper: delete all key lines inside a section
del_key_in_section() {
  local file="$1" section="$2" key="$3"
  local esc
  esc=$(printf '%s' "$section" | sed 's/[][\.^$*+?{}|()]/\\&/g')
  sed -i -E "/^\\[$esc\\]/,/^\\[/{/^[[:space:]]*${key}=.*/d}" "$file" 2>/dev/null || true
}

# Helper: append multiple key=value lines directly after a section header
append_list_after_section() {
  local file="$1" section="$2" key="$3"; shift 3
  local esc
  esc=$(printf '%s' "$section" | sed 's/[][\.^$*+?{}|()]/\\&/g')
  # Append in reverse order to keep final order as provided
  local items=("$@")
  local i
  for (( i=${#items[@]}-1; i>=0; i-- )); do
    [[ -n "${items[$i]}" ]] || continue
    sed -i "/^\\[$esc\\]/a ${key}=${items[$i]}" "$file" 2>/dev/null || true
  done
}

# Discover config directory candidates
discover_config_dir() {
  local base="$1"
  local candidates=(
    "$base/Vein/Saved/Config/LinuxServer"
    "$base/Saved/Config/LinuxServer"
    "$base/Vein/Saved/Config/WindowsServer"
    "$base/Saved/Config/WindowsServer"
  )
  for d in "${candidates[@]}"; do
    if [[ -d "$d" ]]; then
      echo "$d"
      return 0
    fi
  done
  # Default to the first candidate path
  echo "${candidates[0]}"
}

# Build launch arguments from standard env vars
# Safely single-quote values for shell consumption
sh_single_quote() {
  local s="$1"
  # Use bash printf %q to safely escape for shell without wrapping in quotes
  printf "%q" "$s"
}

LAUNCH_ARGS_STR=""
if [[ -n "${SERVER_NAME:-}" ]]; then
  LAUNCH_ARGS_STR+=" -ServerName=$(sh_single_quote "$SERVER_NAME")"
fi
if [[ -n "${SERVER_PASSWORD:-}" ]]; then
  LAUNCH_ARGS_STR+=" -ServerPassword=$(sh_single_quote "$SERVER_PASSWORD")"
fi
if [[ -n "${ADMIN_PASSWORD:-}" ]]; then
  LAUNCH_ARGS_STR+=" -AdminPassword=$(sh_single_quote "$ADMIN_PASSWORD")"
fi
if [[ -n "${SERVER_PORT:-}" ]]; then
  LAUNCH_ARGS_STR+=" -Port=$(sh_single_quote "$SERVER_PORT")"
fi
if [[ -n "${QUERY_PORT:-}" ]]; then
  LAUNCH_ARGS_STR+=" -QueryPort=$(sh_single_quote "$QUERY_PORT")"
fi
if [[ -n "${MAX_PLAYERS:-}" ]]; then
  # Some UE servers accept MaxPlayers as a map option or arg; pass both styles for compatibility
  LAUNCH_ARGS_STR+=" -MaxPlayers=$(sh_single_quote "$MAX_PLAYERS")"
fi
if [[ -n "${STEAM_GSLT:-}" ]]; then
  # Steam Game Server Login Token to establish server ownership
  LAUNCH_ARGS_STR+=" +sv_setsteamaccount $(sh_single_quote "$STEAM_GSLT")"
fi
if [[ -n "${EXTRA_ARGS:-}" ]]; then
  LAUNCH_ARGS_STR+=" ${EXTRA_ARGS}"
fi

echo "📁 Using install dir: ${INSTALL_DIR}"

# Ensure install directory exists and is writable (handle bind mounts)
sudo mkdir -p "$INSTALL_DIR" "$INSTALL_DIR/logs" 2>/dev/null || true
sudo chown -R "$(id -u):$(id -g)" "$INSTALL_DIR" 2>/dev/null || true

echo "🧹 Cleaning up cache..."
rm -rf /home/steam/.cache || true

echo "🔧 Running SteamCMD to ensure dependencies are up to date..."
steamcmd +quit

mkdir -p "$INSTALL_DIR" || true
mkdir -p "$INSTALL_DIR/logs" || true

should_install=false
if [[ ! -d "$INSTALL_DIR" || -z "$(ls -A "$INSTALL_DIR" 2>/dev/null || true)" ]]; then
  should_install=true
fi
if [[ "$UPDATE_ON_START" == "true" ]]; then
  should_install=true
fi

if [[ "$should_install" == "true" ]]; then
  echo "⬇️ Installing/Updating VEIN server (app ${APP_ID})..."
  # Build steamcmd command safely with separate args
  cmd=(steamcmd +force_install_dir "$INSTALL_DIR" +login "$STEAM_USERNAME")
  if [[ -n "$STEAM_PASSWORD" && "$STEAM_USERNAME" != "anonymous" ]]; then
    cmd+=("$STEAM_PASSWORD")
  fi
  cmd+=(+app_update "$APP_ID")
  if [[ "$VALIDATE_FLAG" == "true" ]]; then
    cmd+=(validate)
  fi
  cmd+=(+quit)
  "${cmd[@]}"
fi

# Apply INI settings if enabled
if [[ "$INI_ENABLE" == "true" ]]; then
  CONFIG_DIR="$(discover_config_dir "$INSTALL_DIR")"
  GAME_INI="$CONFIG_DIR/Game.ini"
  # Desired sections per request
  ENGINE_SESSION_SECTION="/script/engine.gamesession"
  VEIN_SESSION_SECTION="/script/vein.veingamesession"

  echo "📝 Applying INI overrides in: $GAME_INI"

  # Ensure sections exist
  ensure_section "$GAME_INI" "$ENGINE_SESSION_SECTION"
  ensure_section "$GAME_INI" "$VEIN_SESSION_SECTION"

  # Engine.GameSession
  if [[ -n "${MAX_PLAYERS:-}" ]]; then
    set_ini_kv "$GAME_INI" "$ENGINE_SESSION_SECTION" "MaxPlayers" "$MAX_PLAYERS"
  fi

  # Vein.VeinGameSession
  # bPublic True/False
  if [[ -n "${SERVER_PUBLIC:-}" ]]; then
    case "${SERVER_PUBLIC,,}" in
      true|1|yes|on) set_ini_kv "$GAME_INI" "$VEIN_SESSION_SECTION" "bPublic" "True" ;;
      *) set_ini_kv "$GAME_INI" "$VEIN_SESSION_SECTION" "bPublic" "False" ;;
    esac
  fi
  if [[ -n "${SERVER_NAME:-}" ]]; then
    set_ini_kv "$GAME_INI" "$VEIN_SESSION_SECTION" "ServerName" "$SERVER_NAME"
  fi
  set_ini_kv "$GAME_INI" "$VEIN_SESSION_SECTION" "BindAddr" "$BIND_ADDR"
  if [[ -n "${HEARTBEAT_INTERVAL:-}" ]]; then
    set_ini_kv "$GAME_INI" "$VEIN_SESSION_SECTION" "HeartbeatInterval" "$HEARTBEAT_INTERVAL"
  fi
  if [[ -n "${SERVER_PASSWORD:-}" ]]; then
    set_ini_kv "$GAME_INI" "$VEIN_SESSION_SECTION" "Password" "$SERVER_PASSWORD"
  fi

  # Admin/SuperAdmin Steam IDs (comma or newline separated)
  if [[ -n "$ADMIN_STEAM_IDS" ]]; then
    # Normalize separators to spaces
    ids=$(printf "%s" "$ADMIN_STEAM_IDS" | tr ',\n' '  ')
    read -r -a id_arr <<< "$ids"
    del_key_in_section "$GAME_INI" "$VEIN_SESSION_SECTION" "AdminSteamIDs"
    append_list_after_section "$GAME_INI" "$VEIN_SESSION_SECTION" "AdminSteamIDs" "${id_arr[@]}"
  fi
  if [[ -n "$SUPERADMIN_STEAM_IDS" ]]; then
    sids=$(printf "%s" "$SUPERADMIN_STEAM_IDS" | tr ',\n' '  ')
    read -r -a sid_arr <<< "$sids"
    del_key_in_section "$GAME_INI" "$VEIN_SESSION_SECTION" "SuperAdminSteamIDs"
    append_list_after_section "$GAME_INI" "$VEIN_SESSION_SECTION" "SuperAdminSteamIDs" "${sid_arr[@]}"
  fi

  # Normalize formatting: remove spaces around equals for all key/value lines
  if command -v sed >/dev/null 2>&1; then
    sed -i -E 's/^([[:space:]]*[^#;][^=]*?)\s*=\s*/\1=/' "$GAME_INI" || true
  fi

  # Optional arbitrary overrides: multiline format file:section:key=value
  if [[ -n "${INI_EXTRA_OVERRIDES:-}" ]]; then
    while IFS= read -r line; do
      # Skip empty or commented lines
      [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
      file=""; part=""; section=""; part2=""; key=""; value=""
      file="${line%%:*}"; part="${line#*:}"
      section="${part%%:*}"; part2="${part#*:}"
      key="${part2%%=*}"; value="${part2#*=}"
    # (Optional) whitespace trimming removed to avoid shell pattern pitfalls
      # Resolve relative file to CONFIG_DIR
      if [[ "$file" != /* ]]; then
        file="$CONFIG_DIR/$file"
      fi
      set_ini_kv "$file" "$section" "$key" "$value"
    done <<< "$INI_EXTRA_OVERRIDES"
  fi
fi

# Preferred: VeinServer.sh in the install directory
if [[ -z "$START_COMMAND" && -f "$INSTALL_DIR/VeinServer.sh" ]]; then
  chmod +x "$INSTALL_DIR/VeinServer.sh" || true
  # Use exec so the shell PID becomes the server PID for proper signal handling
  START_COMMAND="cd \"$INSTALL_DIR\" && exec ./VeinServer.sh${LAUNCH_ARGS_STR}"
fi

if [[ -z "$START_COMMAND" ]]; then
  echo "❌ Could not determine server start command. Set START_COMMAND env var."
  ls -R "$INSTALL_DIR" || true
  exit 1
fi

masked_cmd="$START_COMMAND"
if [[ -n "${SERVER_PASSWORD:-}" ]]; then
  masked_cmd="${masked_cmd//"$SERVER_PASSWORD"/"******"}"
fi
if [[ -n "${ADMIN_PASSWORD:-}" ]]; then
  masked_cmd="${masked_cmd//"$ADMIN_PASSWORD"/"******"}"
fi
echo "🔥 Starting VEIN server with: $masked_cmd"

# Graceful shutdown function: send INT, wait, then TERM/KILL if needed
graceful_shutdown() {
  echo "⏹ Stopping server..."
  local timeout="${SHUTDOWN_TIMEOUT:-30}"
  local patterns=(
    "Vein"
  )

  # Best-effort: send '/save' to server stdin before interrupting
  if [[ "$SAVE_ON_SHUTDOWN" == "true" ]]; then
    send_cmd_to_pid() {
      local pid="$1" cmd="$2"
      # Try using ps to get TTY device
      local tty_name tty_dev
      tty_name=$(ps -o tty= -p "$pid" 2>/dev/null | awk '{print $1}') || true
      if [[ -n "$tty_name" && "$tty_name" != "?" ]]; then
        tty_dev="/dev/${tty_name}"
      else
        # Fallback to fd/0 resolution
        tty_dev=$(readlink -f "/proc/$pid/fd/0" 2>/dev/null || true)
      fi
      if [[ -n "$tty_dev" && -w "$tty_dev" && "$tty_dev" != "/dev/null" ]]; then
        echo "💾 Sending '$cmd' to PID $pid via $tty_dev"
        # Use CRLF for compatibility
        printf "%s\r\n" "$cmd" > "$tty_dev" 2>/dev/null || true
        return 0
      fi
      return 1
    }

    # Attempt to send to main PID
    if kill -0 "$SERVER_PID" 2>/dev/null; then
      send_cmd_to_pid "$SERVER_PID" "Exit" || true
    fi
    # Attempt to send to any matching process as well
    for pat in "${patterns[@]}"; do
      pids=$(pgrep -f "$pat" 2>/dev/null || true)
      if [[ -n "${pids:-}" ]]; then
        for p in $pids; do send_cmd_to_pid "$p" "quit" || true; done
      fi
    done
    echo "⏳ Waiting ${SAVE_WAIT_SECONDS}s for save to complete..."
    sleep "$SAVE_WAIT_SECONDS" || true
  fi

  # Send SIGINT to main PID first
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "🔻 Sending SIGINT to main PID $SERVER_PID"
    kill -INT "$SERVER_PID" 2>/dev/null || true
  fi

  # Also SIGINT any known matching processes (in case of wrappers)
  for pat in "${patterns[@]}"; do
    pids=$(pgrep -f "$pat" 2>/dev/null || true)
    if [[ -n "${pids:-}" ]]; then
      echo "🔻 Sending SIGINT to pattern '$pat' (PIDs: $pids)"
      kill -INT $pids 2>/dev/null || true
    fi
  done

  # Wait for clean exit
  for ((i=0; i<timeout; i++)); do
    alive=false
    if kill -0 "$SERVER_PID" 2>/dev/null; then alive=true; fi
    for pat in "${patterns[@]}"; do
      if pgrep -f "$pat" >/dev/null 2>&1; then alive=true; break; fi
    done
    if [[ "$alive" == false ]]; then
      echo "✅ Server processes stopped."
      return 0
    fi
    sleep 1
  done

  echo "⚠️ Server did not stop after $timeout seconds, sending SIGTERM..."
  if kill -0 "$SERVER_PID" 2>/dev/null; then kill -TERM "$SERVER_PID" 2>/dev/null || true; fi
  for pat in "${patterns[@]}"; do
    pids=$(pgrep -f "$pat" 2>/dev/null || true)
    [[ -n "${pids:-}" ]] && kill -TERM $pids 2>/dev/null || true
  done

  for ((i=0; i<10; i++)); do
    alive=false
    if kill -0 "$SERVER_PID" 2>/dev/null; then alive=true; fi
    for pat in "${patterns[@]}"; do
      if pgrep -f "$pat" >/dev/null 2>&1; then alive=true; break; fi
    done
    if [[ "$alive" == false ]]; then
      echo "✅ Server stopped after SIGTERM."
      return 0
    fi
    sleep 1
  done

  echo "⛔ Forcing termination with SIGKILL..."
  if kill -0 "$SERVER_PID" 2>/dev/null; then kill -KILL "$SERVER_PID" 2>/dev/null || true; fi
  for pat in "${patterns[@]}"; do
    pids=$(pgrep -f "$pat" 2>/dev/null || true)
    [[ -n "${pids:-}" ]] && kill -KILL $pids 2>/dev/null || true
  done
}

# Start server in background
set +e
bash -lc "$START_COMMAND" &
SERVER_PID=$!
set -e

trap 'graceful_shutdown' SIGTERM SIGINT

wait $SERVER_PID

# Final sanity check to ensure no Vein-related processes remain
leftover=$(pgrep -fa "VeinServer|Vein-Win64-Shipping|VeinServer-Win64-Shipping|UE4Server|UE5Server" 2>/dev/null || true)
if [[ -n "${leftover:-}" ]]; then
  echo "⚠️ Leftover processes detected after main process exited:"
  echo "$leftover"
  echo "Attempting clean shutdown..."
  graceful_shutdown || true
fi
