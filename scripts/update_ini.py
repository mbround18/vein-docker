#!/usr/bin/env python3
"""
INI file manipulation for VEIN server Game.ini
Handles Admin and SuperAdmin Steam ID list injection with proper UE4/5 formatting.
Uses configparser for robust INI handling with custom support for UE array syntax (+Key).
"""

import configparser
import re
import sys
from pathlib import Path
from typing import Any


class UEConfigParser(configparser.ConfigParser):
    """
    Custom ConfigParser that preserves UE4/5 array syntax (+Key=value).
    Unreal Engine uses +Key=value for array append operations.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Preserve case for section names and keys
        super().__init__(*args, **kwargs)
        self.optionxform = str  # type: ignore[assignment]

    def write(self, fp: Any, space_around_delimiters: bool = False) -> None:
        """Write INI with custom handling for UE array entries."""
        # Track which sections have been written to add array entries after
        for section in self._sections:  # type: ignore[attr-defined]
            fp.write(f"[{section}]\n")
            section_dict = self._sections[section]  # type: ignore[attr-defined]

            for key, value in section_dict.items():
                if key == "__name__":
                    continue

                # Handle UE array syntax: write both Key=value and +Key=value
                if key.startswith("_ue_array_"):
                    # Extract the real key name
                    real_key = key[len("_ue_array_") :]
                    # Write multiple entries for array
                    if isinstance(value, str) and "\n" in value:
                        # Multiple IDs stored as newline-separated
                        for item in value.split("\n"):
                            if item.strip():
                                fp.write(f"{real_key}={item}\n")
                                fp.write(f"+{real_key}={item}\n")
                    else:
                        fp.write(f"{real_key}={value}\n")
                        fp.write(f"+{real_key}={value}\n")
                else:
                    # Normal key=value
                    if space_around_delimiters:
                        fp.write(f"{key} = {value}\n")
                    else:
                        fp.write(f"{key}={value}\n")

            fp.write("\n")


def remove_ue_array_entries(ini_path: Path, section: str, key: str) -> None:
    """Remove existing UE array entries (both Key= and +Key=) from the file."""
    with ini_path.open("r") as f:
        lines = f.readlines()

    # Remove lines matching both plain and +Key variants
    pattern = re.compile(rf"^\s*\+?{re.escape(key)}=")
    filtered_lines = []
    in_target_section = False

    for line in lines:
        # Track if we're in the target section
        if line.strip().startswith("["):
            in_target_section = line.strip() == f"[{section}]"
            filtered_lines.append(line)
        elif in_target_section and pattern.match(line):
            # Skip lines with our target key in the target section
            continue
        else:
            filtered_lines.append(line)

    with ini_path.open("w") as f:
        f.writelines(filtered_lines)


def update_admin_ids(ini_path: str, section: str, admin_ids: list[str]) -> None:
    """Update AdminSteamIDs in the INI file using configparser."""
    path = Path(ini_path)
    if not path.exists():
        print(f"Error: {ini_path} not found", file=sys.stderr)
        sys.exit(1)

    # First, remove old entries manually (configparser can't handle +Key syntax on read)
    remove_ue_array_entries(path, section, "AdminSteamIDs")

    # Now use configparser to add the section if missing and write new entries
    config = UEConfigParser()
    config.read(path)

    # Ensure section exists
    if not config.has_section(section):
        config.add_section(section)

    # Store array entries with special prefix so our custom writer handles them
    if admin_ids:
        # Store as newline-separated for multiple IDs
        config.set(section, "_ue_array_AdminSteamIDs", "\n".join(admin_ids))

    with path.open("w") as f:
        config.write(f)


def update_superadmin_ids(
    ini_path: str, section: str, superadmin_ids: list[str]
) -> None:
    """Update SuperAdminSteamIDs in the INI file using configparser."""
    path = Path(ini_path)
    if not path.exists():
        print(f"Error: {ini_path} not found", file=sys.stderr)
        sys.exit(1)

    # First, remove old entries manually
    remove_ue_array_entries(path, section, "SuperAdminSteamIDs")

    # Now use configparser to add the section if missing and write new entries
    config = UEConfigParser()
    config.read(path)

    # Ensure section exists
    if not config.has_section(section):
        config.add_section(section)

    # Store array entries with special prefix
    if superadmin_ids:
        config.set(section, "_ue_array_SuperAdminSteamIDs", "\n".join(superadmin_ids))

    with path.open("w") as f:
        config.write(f)


def main():
    if len(sys.argv) < 4:
        print(
            "Usage: update_ini.py <ini_path> <section> <admin|superadmin> [id1] [id2] ...",
            file=sys.stderr,
        )
        sys.exit(1)

    ini_path = sys.argv[1]
    section = sys.argv[2]
    mode = sys.argv[3]
    ids = [id.strip() for id in sys.argv[4:] if id.strip()]

    if mode == "admin":
        update_admin_ids(ini_path, section, ids)
    elif mode == "superadmin":
        update_superadmin_ids(ini_path, section, ids)
    else:
        print(
            f"Error: mode must be 'admin' or 'superadmin', got '{mode}'",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
