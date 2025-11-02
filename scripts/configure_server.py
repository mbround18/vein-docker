#!/usr/bin/env python3
"""
Comprehensive VEIN server configuration script.
Handles Game.ini and GameUserSettings.ini modifications based on environment variables.
"""

import argparse
import configparser
import re
import sys
from pathlib import Path
from typing import Any, Optional


class UEConfigParser(configparser.ConfigParser):
    """
    Custom ConfigParser that preserves UE4/5 array syntax (+Key=value).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.optionxform = str  # type: ignore[assignment]

    def write(self, fp: Any, space_around_delimiters: bool = False) -> None:
        """Write INI with custom handling for UE array entries."""
        for section in self._sections:  # type: ignore[attr-defined]
            fp.write(f"[{section}]\n")
            section_dict = self._sections[section]  # type: ignore[attr-defined]

            for key, value in section_dict.items():
                if key == "__name__":
                    continue

                # Handle UE array syntax
                if key.startswith("_ue_array_"):
                    real_key = key[len("_ue_array_") :]
                    if isinstance(value, str) and "\n" in value:
                        for item in value.split("\n"):
                            if item.strip():
                                fp.write(f"{real_key}={item}\n")
                                fp.write(f"+{real_key}={item}\n")
                    else:
                        fp.write(f"{real_key}={value}\n")
                        fp.write(f"+{real_key}={value}\n")
                else:
                    if space_around_delimiters:
                        fp.write(f"{key} = {value}\n")
                    else:
                        fp.write(f"{key}={value}\n")

            fp.write("\n")


def remove_ue_array_entries(ini_path: Path, section: str, key: str) -> None:
    """Remove existing UE array entries (both Key= and +Key=) from file."""
    if not ini_path.exists():
        return

    try:
        with ini_path.open("r") as f:
            lines = f.readlines()
    except (IOError, OSError) as e:
        print(f"⚠️ Could not read {ini_path}: {e}", file=sys.stderr)
        return

    pattern = re.compile(rf"^\s*\+?{re.escape(key)}=")
    filtered_lines = []
    in_target_section = False

    for line in lines:
        if line.strip().startswith("["):
            in_target_section = line.strip() == f"[{section}]"
            filtered_lines.append(line)
        elif in_target_section and pattern.match(line):
            continue
        else:
            filtered_lines.append(line)

    try:
        with ini_path.open("w") as f:
            f.writelines(filtered_lines)
    except (IOError, OSError) as e:
        print(f"⚠️ Could not write to {ini_path}: {e}", file=sys.stderr)


def update_game_ini(
    config_dir: Path,
    max_players: Optional[str] = None,
    server_public: Optional[str] = None,
    server_name: Optional[str] = None,
    bind_addr: Optional[str] = None,
    heartbeat_interval: Optional[str] = None,
    server_password: Optional[str] = None,
    admin_steam_ids: Optional[list[str]] = None,
    superadmin_steam_ids: Optional[list[str]] = None,
) -> None:
    """Update Game.ini with server settings. Handles fresh installs and updates."""
    game_ini = config_dir / "Game.ini"

    try:
        game_ini.parent.mkdir(parents=True, exist_ok=True)
        game_ini.touch(exist_ok=True)
    except (IOError, OSError) as e:
        print(f"❌ Could not create {game_ini}: {e}", file=sys.stderr)
        return

    engine_section = "/Script/Engine.GameSession"
    vein_section = "/Script/Vein.VeinGameSession"

    # Pre-clean any existing array entries before parsing with ConfigParser
    # This prevents DuplicateOptionError when reading files with UE array syntax
    # Safe to call on fresh installs (no-op if file is empty)
    remove_ue_array_entries(game_ini, vein_section, "AdminSteamIDs")
    remove_ue_array_entries(game_ini, vein_section, "SuperAdminSteamIDs")

    config = UEConfigParser()
    try:
        config.read(game_ini)
    except Exception as e:
        print(
            f"⚠️ Warning reading {game_ini}: {e}. Creating fresh config.",
            file=sys.stderr,
        )
        # Continue with empty config - we'll add sections below

    # Ensure sections exist
    if not config.has_section(engine_section):
        config.add_section(engine_section)
    if not config.has_section(vein_section):
        config.add_section(vein_section)

    # Engine.GameSession settings - only set if provided
    if max_players:
        config.set(engine_section, "MaxPlayers", max_players)

    # Vein.VeinGameSession settings - only set if provided
    if server_public is not None:
        is_public = server_public.lower() in ("true", "1", "yes", "on")
        config.set(vein_section, "bPublic", "True" if is_public else "False")

    if server_name:
        config.set(vein_section, "ServerName", server_name)

    if bind_addr:
        config.set(vein_section, "BindAddr", bind_addr)

    if heartbeat_interval:
        config.set(vein_section, "HeartbeatInterval", heartbeat_interval)

    if server_password:
        config.set(vein_section, "Password", server_password)

    # Handle admin IDs - add them back as special array entries
    # Only add if IDs were provided
    if admin_steam_ids:
        config.set(vein_section, "_ue_array_AdminSteamIDs", "\n".join(admin_steam_ids))

    if superadmin_steam_ids:
        config.set(
            vein_section,
            "_ue_array_SuperAdminSteamIDs",
            "\n".join(superadmin_steam_ids),
        )

    # Write config
    try:
        with game_ini.open("w") as f:
            config.write(f)
        print(f"✅ Updated {game_ini}")
    except (IOError, OSError) as e:
        print(f"❌ Could not write to {game_ini}: {e}", file=sys.stderr)


def update_convar(
    game_user_settings_ini: Path, convar_name: str, convar_value: float
) -> bool:
    """
    Update a console variable in GameUserSettings.ini ConVars array.
    Returns True if successful, False otherwise.
    """
    if not game_user_settings_ini.exists():
        print(
            f"⚠️ {game_user_settings_ini} not found - skipping ConVar update for {convar_name}",
            file=sys.stderr,
        )
        return False

    try:
        with game_user_settings_ini.open("r") as f:
            content = f.read()
    except (IOError, OSError) as e:
        print(
            f"⚠️ Could not read {game_user_settings_ini}: {e}",
            file=sys.stderr,
        )
        return False

    # Find ConVars line
    convar_pattern = re.compile(
        r"(ConVars=\((?:\([^)]+\),?)*\))", re.MULTILINE | re.DOTALL
    )
    match = convar_pattern.search(content)

    if not match:
        print(
            f"⚠️ Could not find ConVars in {game_user_settings_ini} - file may need first-run generation",
            file=sys.stderr,
        )
        return False

    original_convars = match.group(1)

    # Parse individual ConVar entries
    entry_pattern = re.compile(r'\("([^"]+)",\s*([\d.]+)\)')
    entries = entry_pattern.findall(original_convars)

    if not entries:
        print(
            f"⚠️ No ConVar entries found in {game_user_settings_ini}",
            file=sys.stderr,
        )
        return False

    # Update or add the ConVar
    found = False
    updated_entries = []
    for key, value in entries:
        if key == convar_name:
            updated_entries.append((key, convar_value))
            found = True
        else:
            try:
                updated_entries.append((key, float(value)))
            except ValueError:
                print(f"⚠️ Invalid float value for {key}: {value}", file=sys.stderr)
                updated_entries.append((key, 0.0))

    # Add new ConVar if not found
    if not found:
        updated_entries.append((convar_name, convar_value))

    # Rebuild ConVars line
    formatted_entries = ",".join([f'("{k}", {v:f})' for k, v in updated_entries])
    new_convars = f"ConVars=({formatted_entries})"

    # Replace in content
    updated_content = content.replace(original_convars, new_convars)

    try:
        with game_user_settings_ini.open("w") as f:
            f.write(updated_content)
        return True
    except (IOError, OSError) as e:
        print(
            f"⚠️ Could not write to {game_user_settings_ini}: {e}",
            file=sys.stderr,
        )
        return False


def update_game_user_settings(
    config_dir: Path,
    autosave_enabled: Optional[str] = None,
    autosave_interval: Optional[str] = None,
    autosave_max_quantity: Optional[str] = None,
) -> None:
    """Update GameUserSettings.ini with ConVars. Handles missing files gracefully."""
    game_user_settings = config_dir / "GameUserSettings.ini"

    if not game_user_settings.exists():
        print(
            f"⚠️ {game_user_settings} not found - ConVar updates will be skipped. "
            "This file should be generated on first server run.",
            file=sys.stderr,
        )
        return

    # Track if any updates were successful
    updated = False

    try:
        if autosave_enabled is not None:
            if update_convar(
                game_user_settings, "vein.Autosave.Enabled", float(autosave_enabled)
            ):
                updated = True

        if autosave_interval is not None:
            if update_convar(
                game_user_settings, "vein.Autosave.Interval", float(autosave_interval)
            ):
                updated = True

        if autosave_max_quantity is not None:
            if update_convar(
                game_user_settings,
                "vein.Autosave.MaxQuantity",
                float(autosave_max_quantity),
            ):
                updated = True

        if updated:
            print(f"✅ Updated {game_user_settings}")
        else:
            print(f"ℹ️ No ConVar changes made to {game_user_settings}")
    except ValueError as e:
        print(f"❌ Invalid numeric value for autosave settings: {e}", file=sys.stderr)


def parse_env_list(value: Optional[str]) -> list[str]:
    """Parse comma or newline separated list from environment variable."""
    if not value:
        return []
    # Replace commas and newlines with spaces, then split
    normalized = value.replace(",", " ").replace("\n", " ")
    return [item.strip() for item in normalized.split() if item.strip()]


def main() -> None:
    """Main entry point for VEIN server configuration."""
    parser = argparse.ArgumentParser(
        description="Configure VEIN server INI files from environment variables. "
        "Supports fresh installs, updates, and missing file scenarios."
    )
    parser.add_argument("config_dir", type=Path, help="Path to config directory")
    parser.add_argument("--max-players", help="Maximum players")
    parser.add_argument("--server-public", help="Server public visibility (true/false)")
    parser.add_argument("--server-name", help="Server name")
    parser.add_argument("--bind-addr", help="Bind address")
    parser.add_argument("--heartbeat-interval", help="Heartbeat interval")
    parser.add_argument("--server-password", help="Server password")
    parser.add_argument(
        "--admin-steam-ids", help="Comma or newline separated admin Steam IDs"
    )
    parser.add_argument(
        "--superadmin-steam-ids",
        help="Comma or newline separated superadmin Steam IDs",
    )
    parser.add_argument("--autosave-enabled", help="Autosave enabled (0/1)")
    parser.add_argument("--autosave-interval", help="Autosave interval in seconds")
    parser.add_argument(
        "--autosave-max-quantity", help="Maximum number of autosave files"
    )

    args = parser.parse_args()

    config_dir = args.config_dir

    # Ensure config directory exists
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except (IOError, OSError) as e:
        print(
            f"❌ Could not create config directory {config_dir}: {e}", file=sys.stderr
        )
        sys.exit(1)

    # Parse Steam ID lists (empty lists are fine - means no IDs to set)
    admin_ids = parse_env_list(args.admin_steam_ids)
    superadmin_ids = parse_env_list(args.superadmin_steam_ids)

    # Update Game.ini (always runs, safe for fresh installs and updates)
    print("📝 Configuring Game.ini...")
    update_game_ini(
        config_dir,
        max_players=args.max_players,
        server_public=args.server_public,
        server_name=args.server_name,
        bind_addr=args.bind_addr,
        heartbeat_interval=args.heartbeat_interval,
        server_password=args.server_password,
        admin_steam_ids=admin_ids if admin_ids else None,
        superadmin_steam_ids=superadmin_ids if superadmin_ids else None,
    )

    # Update GameUserSettings.ini (gracefully handles missing files)
    print("📝 Configuring GameUserSettings.ini...")
    update_game_user_settings(
        config_dir,
        autosave_enabled=args.autosave_enabled,
        autosave_interval=args.autosave_interval,
        autosave_max_quantity=args.autosave_max_quantity,
    )

    print("✨ Configuration complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Configuration interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error during configuration: {e}", file=sys.stderr)
        sys.exit(1)
