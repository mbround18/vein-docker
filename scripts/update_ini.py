#!/usr/bin/env python3
"""
INI file manipulation for VEIN server Game.ini
Handles Admin and SuperAdmin Steam ID list injection with proper UE4/5 formatting.
"""

import re
import sys
from pathlib import Path


def remove_matching_lines(lines: list[str], pattern: str) -> list[str]:
    """Remove lines matching the given regex pattern."""
    compiled = re.compile(pattern)
    return [line for line in lines if not compiled.match(line)]


def inject_ids_after_section(
    lines: list[str], section: str, key: str, ids: list[str]
) -> list[str]:
    """
    Inject ID entries after the section header.
    Writes both Key=value and +Key=value forms for UE4/5 array handling.
    """
    out = []
    injected = False

    for line in lines:
        out.append(line)
        # Check if this is the target section header
        if line.strip() == f"[{section}]":
            if not injected and ids:
                for steam_id in ids:
                    if steam_id.strip():
                        out.append(f"{key}={steam_id.strip()}\n")
                        out.append(f"+{key}={steam_id.strip()}\n")
                injected = True

    return out


def update_admin_ids(ini_path: str, section: str, admin_ids: list[str]) -> None:
    """Update AdminSteamIDs in the INI file."""
    path = Path(ini_path)
    if not path.exists():
        print(f"Error: {ini_path} not found", file=sys.stderr)
        sys.exit(1)

    with path.open("r") as f:
        lines = f.readlines()

    # Remove old admin entries (both plain and +Key variants)
    lines = remove_matching_lines(lines, r"^\s*\+?AdminSteamIDs=")

    # Inject new admin entries
    lines = inject_ids_after_section(lines, section, "AdminSteamIDs", admin_ids)

    with path.open("w") as f:
        f.writelines(lines)


def update_superadmin_ids(
    ini_path: str, section: str, superadmin_ids: list[str]
) -> None:
    """Update SuperAdminSteamIDs in the INI file."""
    path = Path(ini_path)
    if not path.exists():
        print(f"Error: {ini_path} not found", file=sys.stderr)
        sys.exit(1)

    with path.open("r") as f:
        lines = f.readlines()

    # Remove old superadmin entries (both plain and +Key variants)
    lines = remove_matching_lines(lines, r"^\s*\+?SuperAdminSteamIDs=")

    # Inject new superadmin entries
    lines = inject_ids_after_section(
        lines, section, "SuperAdminSteamIDs", superadmin_ids
    )

    with path.open("w") as f:
        f.writelines(lines)


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
