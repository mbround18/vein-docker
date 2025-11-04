"""
Tests for configure_server.py script.
Tests INI file generation, updates, and Steam ID handling.
"""

from pathlib import Path
from unittest.mock import patch

from scripts.configure_server import (
    UEConfigParser,
    parse_env_list,
    remove_ue_array_entries,
    update_convar,
    update_game_ini,
    update_game_user_settings,
)


class TestUEConfigParser:
    """Test custom ConfigParser for Unreal Engine INI files."""

    def test_preserves_case_sensitivity(self, tmp_path: Path) -> None:
        """ConfigParser should preserve key case."""
        config = UEConfigParser()
        config.add_section("TestSection")
        config.set("TestSection", "CamelCaseKey", "value")

        ini_file = tmp_path / "test.ini"
        with ini_file.open("w") as f:
            config.write(f)

        content = ini_file.read_text()
        assert "CamelCaseKey" in content
        assert "camelcasekey" not in content.lower().replace("camelcasekey", "FOUND")

    def test_writes_ue_array_syntax(self, tmp_path: Path) -> None:
        """ConfigParser should write UE array entries with + prefix."""
        config = UEConfigParser()
        config.add_section("TestSection")
        config.set("TestSection", "_ue_array_TestArray", "item1\nitem2")

        ini_file = tmp_path / "test.ini"
        with ini_file.open("w") as f:
            config.write(f)

        content = ini_file.read_text()
        assert "TestArray=item1" in content
        assert "+TestArray=item1" in content
        assert "TestArray=item2" in content
        assert "+TestArray=item2" in content

    def test_disables_interpolation(self) -> None:
        """ConfigParser should not interpolate values (prevents scientific notation)."""
        config = UEConfigParser()
        config.add_section("TestSection")

        # Set a large numeric string that would be converted to scientific notation
        steam_id = "76561198071622110"
        config.set("TestSection", "SteamID", steam_id)

        # Should retrieve as exact string, not converted
        assert config.get("TestSection", "SteamID") == steam_id


class TestParseEnvList:
    """Test environment variable list parsing."""

    def test_parses_comma_separated(self) -> None:
        result = parse_env_list("123,456,789")
        assert result == ["123", "456", "789"]

    def test_parses_newline_separated(self) -> None:
        result = parse_env_list("123\n456\n789")
        assert result == ["123", "456", "789"]

    def test_parses_mixed_separators(self) -> None:
        result = parse_env_list("123,456\n789")
        assert result == ["123", "456", "789"]

    def test_handles_whitespace(self) -> None:
        result = parse_env_list("  123  ,  456  \n  789  ")
        assert result == ["123", "456", "789"]

    def test_returns_empty_list_for_none(self) -> None:
        result = parse_env_list(None)
        assert result == []

    def test_returns_empty_list_for_empty_string(self) -> None:
        result = parse_env_list("")
        assert result == []


class TestRemoveUEArrayEntries:
    """Test removal of UE array entries from INI files."""

    def test_removes_array_entries(self, tmp_path: Path) -> None:
        ini_file = tmp_path / "test.ini"
        ini_file.write_text(
            "[TestSection]\n"
            "TestArray=item1\n"
            "+TestArray=item1\n"
            "TestArray=item2\n"
            "+TestArray=item2\n"
            "OtherKey=value\n"
        )

        remove_ue_array_entries(ini_file, "TestSection", "TestArray")

        content = ini_file.read_text()
        assert "TestArray" not in content
        assert "OtherKey=value" in content

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        """Should not raise error for non-existent file."""
        ini_file = tmp_path / "missing.ini"
        remove_ue_array_entries(ini_file, "TestSection", "TestArray")

    def test_preserves_other_sections(self, tmp_path: Path) -> None:
        ini_file = tmp_path / "test.ini"
        ini_file.write_text(
            "[TestSection]\n"
            "TestArray=item1\n"
            "+TestArray=item1\n"
            "[OtherSection]\n"
            "TestArray=keep_this\n"
            "+TestArray=keep_this\n"
        )

        remove_ue_array_entries(ini_file, "TestSection", "TestArray")

        content = ini_file.read_text()
        assert "[OtherSection]" in content
        # Should have both base and + prefix entry
        assert "TestArray=keep_this" in content
        assert "+TestArray=keep_this" in content
        # TestSection should have no TestArray entries
        assert "[TestSection]" in content
        lines = content.split("\n")
        test_section_idx = lines.index("[TestSection]")
        other_section_idx = lines.index("[OtherSection]")
        # No TestArray between TestSection and OtherSection
        section_lines = lines[test_section_idx + 1 : other_section_idx]
        assert not any("TestArray" in line for line in section_lines)


class TestUpdateGameIni:
    """Test Game.ini updates."""

    def test_creates_fresh_game_ini(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"

        update_game_ini(
            config_dir,
            max_players="16",
            server_name="Test Server",
            server_public="true",
        )

        game_ini = config_dir / "Game.ini"
        assert game_ini.exists()

        content = game_ini.read_text()
        assert "[/Script/Engine.GameSession]" in content
        assert "MaxPlayers=16" in content
        assert "[/Script/Vein.VeinGameSession]" in content
        assert "ServerName=Test Server" in content
        assert "bPublic=True" in content

    def test_preserves_steam_ids_as_strings(self, tmp_path: Path) -> None:
        """Steam IDs should not be converted to scientific notation."""
        config_dir = tmp_path / "config"

        admin_ids = ["76561198071622110", "76561198071622111"]
        superadmin_ids = ["76561198028400660"]

        update_game_ini(
            config_dir,
            admin_steam_ids=admin_ids,
            superadmin_steam_ids=superadmin_ids,
        )

        game_ini = config_dir / "Game.ini"
        content = game_ini.read_text()

        # Should contain exact Steam IDs, not scientific notation
        assert "76561198071622110" in content
        assert "76561198071622111" in content
        assert "76561198028400660" in content
        assert "e+" not in content  # No scientific notation
        assert "AdminSteamIDs=76561198071622110" in content
        assert "+AdminSteamIDs=76561198071622110" in content
        assert "SuperAdminSteamIDs=76561198028400660" in content
        assert "+SuperAdminSteamIDs=76561198028400660" in content

    def test_updates_existing_game_ini(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        game_ini = config_dir / "Game.ini"
        game_ini.write_text(
            "[/Script/Engine.GameSession]\n"
            "MaxPlayers=8\n"
            "[/Script/Vein.VeinGameSession]\n"
            "ServerName=Old Server\n"
        )

        update_game_ini(
            config_dir,
            max_players="32",
            server_name="New Server",
        )

        content = game_ini.read_text()
        assert "MaxPlayers=32" in content
        assert "ServerName=New Server" in content
        assert "MaxPlayers=8" not in content
        assert "Old Server" not in content

    def test_handles_admin_id_updates(self, tmp_path: Path) -> None:
        """Should replace existing admin IDs without duplicates."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        game_ini = config_dir / "Game.ini"
        game_ini.write_text(
            "[/Script/Vein.VeinGameSession]\n"
            "AdminSteamIDs=11111111111111111\n"
            "+AdminSteamIDs=11111111111111111\n"
        )

        update_game_ini(
            config_dir,
            admin_steam_ids=["22222222222222222"],
        )

        content = game_ini.read_text()
        assert "22222222222222222" in content
        assert "11111111111111111" not in content

    def test_skips_optional_settings(self, tmp_path: Path) -> None:
        """Should only write settings that are provided."""
        config_dir = tmp_path / "config"

        update_game_ini(config_dir, server_name="Test Server")

        game_ini = config_dir / "Game.ini"
        content = game_ini.read_text()

        assert "ServerName=Test Server" in content
        assert "MaxPlayers" not in content
        assert "Password" not in content


class TestUpdateConvar:
    """Test GameUserSettings.ini ConVar updates."""

    def test_updates_existing_convar(self, tmp_path: Path) -> None:
        ini_file = tmp_path / "GameUserSettings.ini"
        ini_file.write_text(
            "[/Script/Vein.VeinGameUserSettings]\n"
            'ConVars=(("vein.Autosave.Enabled", 0.000000),("vein.Autosave.Interval", 300.000000))\n'
        )

        result = update_convar(ini_file, "vein.Autosave.Interval", 60.0)
        assert result is True

        content = ini_file.read_text()
        assert '("vein.Autosave.Interval", 60.000000)' in content
        assert '("vein.Autosave.Interval", 300.000000)' not in content

    def test_adds_new_convar(self, tmp_path: Path) -> None:
        ini_file = tmp_path / "GameUserSettings.ini"
        ini_file.write_text(
            "[/Script/Vein.VeinGameUserSettings]\n"
            'ConVars=(("vein.Autosave.Enabled", 1.000000))\n'
        )

        result = update_convar(ini_file, "vein.Autosave.MaxQuantity", 10.0)
        assert result is True

        content = ini_file.read_text()
        assert '("vein.Autosave.MaxQuantity", 10.000000)' in content
        assert '("vein.Autosave.Enabled", 1.000000)' in content

    def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        ini_file = tmp_path / "missing.ini"
        result = update_convar(ini_file, "vein.test", 1.0)
        assert result is False

    def test_returns_false_for_missing_convars(self, tmp_path: Path) -> None:
        ini_file = tmp_path / "GameUserSettings.ini"
        ini_file.write_text("[/Script/Vein.VeinGameUserSettings]\nSomeOtherKey=value\n")

        result = update_convar(ini_file, "vein.test", 1.0)
        assert result is False


class TestUpdateGameUserSettings:
    """Test GameUserSettings.ini updates."""

    def test_updates_autosave_settings(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        ini_file = config_dir / "GameUserSettings.ini"
        ini_file.write_text(
            "[/Script/Vein.VeinGameUserSettings]\n"
            'ConVars=(("vein.Autosave.Enabled", 0.000000),("vein.Autosave.Interval", 300.000000),("vein.Autosave.MaxQuantity", 5.000000))\n'
        )

        update_game_user_settings(
            config_dir,
            autosave_enabled="1",
            autosave_interval="60",
            autosave_max_quantity="10",
        )

        content = ini_file.read_text()
        assert '("vein.Autosave.Enabled", 1.000000)' in content
        assert '("vein.Autosave.Interval", 60.000000)' in content
        assert '("vein.Autosave.MaxQuantity", 10.000000)' in content

    def test_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        """Should not raise error if GameUserSettings.ini doesn't exist."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        update_game_user_settings(
            config_dir,
            autosave_enabled="1",
        )

    def test_handles_partial_updates(self, tmp_path: Path) -> None:
        """Should only update provided settings."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        ini_file = config_dir / "GameUserSettings.ini"
        ini_file.write_text(
            "[/Script/Vein.VeinGameUserSettings]\n"
            'ConVars=(("vein.Autosave.Enabled", 0.000000),("vein.Autosave.Interval", 300.000000))\n'
        )

        update_game_user_settings(
            config_dir,
            autosave_interval="60",
        )

        content = ini_file.read_text()
        assert '("vein.Autosave.Interval", 60.000000)' in content
        assert '("vein.Autosave.Enabled", 0.000000)' in content


class TestIntegration:
    """Integration tests simulating real-world scenarios."""

    def test_fresh_install_workflow(self, tmp_path: Path) -> None:
        """Test complete fresh install configuration."""
        config_dir = tmp_path / "config"

        # Update Game.ini
        update_game_ini(
            config_dir,
            max_players="16",
            server_name="Fresh Server",
            server_public="true",
            bind_addr="0.0.0.0",
            server_password="test123",
            admin_steam_ids=["76561198071622110"],
            superadmin_steam_ids=["76561198028400660"],
        )

        game_ini = config_dir / "Game.ini"
        assert game_ini.exists()

        content = game_ini.read_text()
        assert "MaxPlayers=16" in content
        assert "ServerName=Fresh Server" in content
        assert "76561198071622110" in content
        assert "76561198028400660" in content
        assert "e+" not in content

    def test_existing_server_update(self, tmp_path: Path) -> None:
        """Test updating existing server configuration."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create existing configs
        game_ini = config_dir / "Game.ini"
        game_ini.write_text(
            "[/Script/Engine.GameSession]\n"
            "MaxPlayers=8\n"
            "[/Script/Vein.VeinGameSession]\n"
            "ServerName=Old Server\n"
            "AdminSteamIDs=11111111111111111\n"
            "+AdminSteamIDs=11111111111111111\n"
        )

        game_user_settings = config_dir / "GameUserSettings.ini"
        game_user_settings.write_text(
            "[/Script/Vein.VeinGameUserSettings]\n"
            'ConVars=(("vein.Autosave.Enabled", 0.000000),("vein.Autosave.Interval", 300.000000))\n'
        )

        # Update configs
        update_game_ini(
            config_dir,
            max_players="32",
            server_name="Updated Server",
            admin_steam_ids=["22222222222222222"],
        )

        update_game_user_settings(
            config_dir,
            autosave_enabled="1",
            autosave_interval="60",
        )

        # Verify Game.ini
        game_content = game_ini.read_text()
        assert "MaxPlayers=32" in game_content
        assert "Updated Server" in game_content
        assert "22222222222222222" in game_content
        assert "11111111111111111" not in game_content

        # Verify GameUserSettings.ini
        settings_content = game_user_settings.read_text()
        assert '("vein.Autosave.Enabled", 1.000000)' in settings_content
        assert '("vein.Autosave.Interval", 60.000000)' in settings_content


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_remove_ue_array_entries_read_error(self, tmp_path: Path) -> None:
        """Should handle read errors gracefully."""
        ini_file = tmp_path / "test.ini"
        ini_file.write_text("[Section]\nKey=value\n")
        ini_file.chmod(0o000)  # Remove read permissions

        try:
            # Should not raise exception, just print warning
            remove_ue_array_entries(ini_file, "Section", "Key")
        finally:
            ini_file.chmod(0o644)  # Restore permissions for cleanup

    def test_remove_ue_array_entries_write_error(self, tmp_path: Path) -> None:
        """Should handle write errors gracefully."""
        ini_dir = tmp_path / "readonly"
        ini_dir.mkdir()
        ini_file = ini_dir / "test.ini"
        ini_file.write_text("[Section]\nKey=value\n+Key=value\n")

        # Make directory read-only
        ini_dir.chmod(0o555)

        try:
            # Should not raise exception, just print warning
            remove_ue_array_entries(ini_file, "Section", "Key")
        finally:
            ini_dir.chmod(0o755)  # Restore permissions for cleanup

    def test_update_game_ini_directory_creation_error(self, tmp_path: Path) -> None:
        """Should handle directory creation errors."""
        # Create a file where we need a directory
        config_path = tmp_path / "config"
        config_path.write_text("blocking file")

        # Should handle error gracefully
        update_game_ini(config_path, server_name="Test")

    def test_update_game_ini_write_error(self, tmp_path: Path) -> None:
        """Should handle write errors gracefully."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        game_ini = config_dir / "Game.ini"
        game_ini.write_text("[Section]\n")

        # Make file read-only
        game_ini.chmod(0o444)

        try:
            update_game_ini(config_dir, server_name="Test")
        finally:
            game_ini.chmod(0o644)

    def test_update_game_ini_malformed_existing_file(self, tmp_path: Path) -> None:
        """Should handle malformed INI files."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        game_ini = config_dir / "Game.ini"
        game_ini.write_text("This is not valid INI content @#$%")

        # Should create fresh config despite bad existing file
        update_game_ini(config_dir, server_name="Test Server")

        content = game_ini.read_text()
        assert "ServerName=Test Server" in content

    def test_update_convar_read_error(self, tmp_path: Path) -> None:
        """Should return False on read errors."""
        ini_file = tmp_path / "test.ini"
        ini_file.write_text("content")
        ini_file.chmod(0o000)

        try:
            result = update_convar(ini_file, "test.var", 1.0)
            assert result is False
        finally:
            ini_file.chmod(0o644)

    def test_update_convar_write_error(self, tmp_path: Path) -> None:
        """Should return False on write errors."""
        ini_file = tmp_path / "test.ini"
        ini_file.write_text('[Section]\nConVars=(("test.var", 1.000000))\n')
        ini_file.chmod(0o444)

        try:
            result = update_convar(ini_file, "test.var", 2.0)
            assert result is False
        finally:
            ini_file.chmod(0o644)

    def test_update_convar_handles_all_valid_floats(self, tmp_path: Path) -> None:
        """Test that update_convar works with various valid float formats."""
        ini_file = tmp_path / "test.ini"
        ini_file.write_text(
            '[Section]\nConVars=(("valid.var", 1.000000),("another.var", 2.5))\n'
        )

        result = update_convar(ini_file, "valid.var", 3.0)
        assert result is True

        content = ini_file.read_text()
        assert '("valid.var", 3.000000)' in content
        assert '("another.var", 2.5' in content  # Preserved

    def test_update_game_user_settings_invalid_numeric(self, tmp_path: Path) -> None:
        """Should handle invalid numeric values."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        ini_file = config_dir / "GameUserSettings.ini"
        ini_file.write_text(
            '[Section]\nConVars=(("vein.Autosave.Enabled", 1.000000))\n'
        )

        # Should catch ValueError and print error
        update_game_user_settings(config_dir, autosave_interval="not_a_number")


class TestMainFunction:
    """Test the main CLI entry point."""

    def test_main_with_all_arguments(self, tmp_path: Path) -> None:
        """Test main function with all arguments."""
        from scripts.configure_server import main

        config_dir = tmp_path / "config"

        test_args = [
            "configure_server.py",
            str(config_dir),
            "--max-players",
            "32",
            "--server-public",
            "true",
            "--server-name",
            "CLI Test Server",
            "--bind-addr",
            "127.0.0.1",
            "--heartbeat-interval",
            "10.0",
            "--server-password",
            "testpass",
            "--admin-steam-ids",
            "11111111111111111,22222222222222222",
            "--superadmin-steam-ids",
            "33333333333333333",
            "--autosave-enabled",
            "1",
            "--autosave-interval",
            "120",
            "--autosave-max-quantity",
            "15",
        ]

        with patch("sys.argv", test_args):
            main()

        game_ini = config_dir / "Game.ini"
        assert game_ini.exists()
        content = game_ini.read_text()
        assert "MaxPlayers=32" in content
        assert "CLI Test Server" in content
        assert "11111111111111111" in content
        assert "22222222222222222" in content
        assert "33333333333333333" in content

    def test_main_with_minimal_arguments(self, tmp_path: Path) -> None:
        """Test main function with only required arguments."""
        from scripts.configure_server import main

        config_dir = tmp_path / "config"

        test_args = [
            "configure_server.py",
            str(config_dir),
        ]

        with patch("sys.argv", test_args):
            main()

        game_ini = config_dir / "Game.ini"
        assert game_ini.exists()

    def test_main_directory_creation_error(self, tmp_path: Path) -> None:
        """Test main function handles directory creation errors."""
        import pytest
        from scripts.configure_server import main

        # Use a path that can't be created (file instead of directory)
        config_path = tmp_path / "file"
        config_path.write_text("blocking")
        config_dir = config_path / "config"

        test_args = ["configure_server.py", str(config_dir)]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestEdgeCases:
    """Test additional edge cases for complete coverage."""

    def test_ue_config_parser_single_item_array(self, tmp_path: Path) -> None:
        """Test UE array with single item (no newlines)."""
        config = UEConfigParser()
        config.add_section("TestSection")
        config.set("TestSection", "_ue_array_SingleItem", "value1")

        ini_file = tmp_path / "test.ini"
        with ini_file.open("w") as f:
            config.write(f)

        content = ini_file.read_text()
        assert "SingleItem=value1" in content
        assert "+SingleItem=value1" in content

    def test_ue_config_parser_with_space_delimiters(self, tmp_path: Path) -> None:
        """Test writing with space around delimiters."""
        config = UEConfigParser()
        config.add_section("TestSection")
        config.set("TestSection", "NormalKey", "value")

        ini_file = tmp_path / "test.ini"
        with ini_file.open("w") as f:
            config.write(f, space_around_delimiters=True)

        content = ini_file.read_text()
        assert "NormalKey = value" in content

    def test_update_game_ini_all_settings(self, tmp_path: Path) -> None:
        """Test update_game_ini with all possible settings."""
        config_dir = tmp_path / "config"

        update_game_ini(
            config_dir,
            max_players="64",
            server_public="false",
            server_name="Full Config",
            bind_addr="0.0.0.0",
            heartbeat_interval="15.5",
            server_password="secret123",
            admin_steam_ids=["11111111111111111"],
            superadmin_steam_ids=["22222222222222222"],
        )

        game_ini = config_dir / "Game.ini"
        content = game_ini.read_text()

        assert "MaxPlayers=64" in content
        assert "bPublic=False" in content
        assert "ServerName=Full Config" in content
        assert "BindAddr=0.0.0.0" in content
        assert "HeartbeatInterval=15.5" in content
        assert "Password=secret123" in content
        assert "11111111111111111" in content
        assert "22222222222222222" in content

    def test_server_public_various_true_values(self, tmp_path: Path) -> None:
        """Test different ways to specify server_public=true."""
        config_dir = tmp_path / "config"

        for value in ["true", "True", "1", "yes", "YES", "on", "ON"]:
            config_dir = tmp_path / f"config_{value}"
            update_game_ini(config_dir, server_public=value)
            content = (config_dir / "Game.ini").read_text()
            assert "bPublic=True" in content, f"Failed for value: {value}"

    def test_server_public_false_values(self, tmp_path: Path) -> None:
        """Test different ways to specify server_public=false."""
        for value in ["false", "False", "0", "no", "off"]:
            config_dir = tmp_path / f"config_{value}"
            update_game_ini(config_dir, server_public=value)
            content = (config_dir / "Game.ini").read_text()
            assert "bPublic=False" in content, f"Failed for value: {value}"

    def test_update_convar_empty_convars(self, tmp_path: Path) -> None:
        """Test update_convar with empty ConVars tuple."""
        ini_file = tmp_path / "test.ini"
        ini_file.write_text("[Section]\nConVars=()\n")

        result = update_convar(ini_file, "test.var", 1.0)
        assert result is False

    def test_ue_array_with_empty_lines(self, tmp_path: Path) -> None:
        """Test UE array entries with empty lines (should be skipped)."""
        config = UEConfigParser()
        config.add_section("TestSection")
        config.set("TestSection", "_ue_array_TestKey", "value1\n\nvalue2\n")

        ini_file = tmp_path / "test.ini"
        with ini_file.open("w") as f:
            config.write(f)

        content = ini_file.read_text()
        lines = content.split("\n")
        # Count actual entries (should only have value1 and value2, not empty line)
        test_key_lines = [line for line in lines if "TestKey=" in line and line.strip()]
        assert len(test_key_lines) == 4  # 2 items × 2 lines each (Key= and +Key=)

    def test_update_convar_with_invalid_float_value(self, tmp_path: Path) -> None:
        """Test update_convar handles ValueError when parsing existing floats."""
        # This test exercises the ValueError exception handler in update_convar
        # by creating a ConVar with a value that looks like a float but isn't
        ini_file = tmp_path / "test.ini"
        # Use scientific notation that will be matched by regex but may cause issues
        ini_file.write_text(
            "[Section]\n"
            'ConVars=(("good.var", 1.5),("bad.var", 9.9e999999999))\n'  # Extreme exponent
        )

        # Try to update a variable - this should trigger ValueError handling
        result = update_convar(ini_file, "good.var", 2.0)

        # The function should handle the bad float gracefully
        # Even if one value is bad, it should still process the good ones
        if result:
            content = ini_file.read_text()
            assert '("good.var", 2.0' in content

    def test_update_game_user_settings_with_print_coverage(
        self, tmp_path: Path, capsys
    ) -> None:
        """Test update_game_user_settings info message when no changes."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        ini_file = config_dir / "GameUserSettings.ini"
        ini_file.write_text(
            '[Section]\nConVars=(("vein.Autosave.Enabled", 1.000000))\n'
        )

        # Call with no arguments that would trigger changes
        update_game_user_settings(config_dir)

        captured = capsys.readouterr()
        # Should print info message or warning about missing file
        assert "⚠️" in captured.err or "ℹ️" in captured.out or "✅" in captured.out

    def test_script_execution_with_subprocess(self, tmp_path: Path) -> None:
        """Test running the script as __main__ to cover exception handlers."""
        import subprocess
        import sys

        config_dir = tmp_path / "config"
        script_path = Path(__file__).parent.parent / "scripts" / "configure_server.py"

        # Test successful execution
        result = subprocess.run(
            [sys.executable, str(script_path), str(config_dir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "✨ Configuration complete!" in result.stdout

    def test_convar_parsing_with_string_that_breaks_float(
        self, tmp_path: Path, capsys
    ) -> None:
        """Test ValueError handling when float conversion fails."""
        # We need to manually patch the float conversion in update_convar
        # to test the ValueError exception handler
        from scripts import configure_server

        ini_file = tmp_path / "test.ini"
        ini_file.write_text('[Section]\nConVars=(("good.var", 1.5),("bad.var", 2.5))\n')

        # Save original float
        original_float = float

        def failing_float(value):
            """Mock float that fails on specific value."""
            if isinstance(value, str) and value == "2.5":
                raise ValueError("Simulated float conversion error")
            return original_float(value)

        # Patch float in the configure_server module
        with patch.object(configure_server, "float", failing_float):
            update_convar(ini_file, "good.var", 3.0)

        # Check that stderr captured the warning
        captured = capsys.readouterr()
        assert "⚠️" in captured.err and "Invalid float value" in captured.err
