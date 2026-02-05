#!/usr/bin/env python3
"""Tests for the config module."""

import pytest

from keymap_align.config import find_config_file
from keymap_align.config import load_config
from keymap_align.config import resolve_config_layout


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_finds_config_in_same_directory(self, tmp_path):
        """Should find config file in the same directory."""
        config_file = tmp_path / 'keymap_align.toml'
        config_file.write_text('layout = "corne42"')

        result = find_config_file(tmp_path)
        assert result == config_file

    def test_finds_config_in_parent_directory(self, tmp_path):
        """Should find config file in parent directory."""
        config_file = tmp_path / 'keymap_align.toml'
        config_file.write_text('layout = "corne42"')

        subdir = tmp_path / 'subdir'
        subdir.mkdir()

        result = find_config_file(subdir)
        assert result == config_file

    def test_finds_config_in_grandparent_directory(self, tmp_path):
        """Should find config file in grandparent directory."""
        config_file = tmp_path / 'keymap_align.toml'
        config_file.write_text('layout = "corne42"')

        subdir = tmp_path / 'subdir' / 'nested'
        subdir.mkdir(parents=True)

        result = find_config_file(subdir)
        assert result == config_file

    def test_returns_none_when_no_config(self, tmp_path):
        """Should return None when no config file exists."""
        result = find_config_file(tmp_path)
        assert result is None

    def test_prefers_closer_config_file(self, tmp_path):
        """Should prefer config file closer to start path."""
        parent_config = tmp_path / 'keymap_align.toml'
        parent_config.write_text('layout = "corne42"')

        subdir = tmp_path / 'subdir'
        subdir.mkdir()

        subdir_config = subdir / 'keymap_align.toml'
        subdir_config.write_text('layout = "piantor"')

        result = find_config_file(subdir)
        assert result == subdir_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_valid_toml(self, tmp_path):
        """Should load valid TOML config."""
        config_file = tmp_path / 'keymap_align.toml'
        config_file.write_text('layout = "corne42"\ndebug = true')

        result = load_config(config_file)
        assert result == {'layout': 'corne42', 'debug': True}

    def test_raises_for_invalid_toml(self, tmp_path):
        """Should raise error for invalid TOML."""
        import tomllib

        config_file = tmp_path / 'keymap_align.toml'
        config_file.write_text('invalid = [missing bracket')

        with pytest.raises(tomllib.TOMLDecodeError):
            load_config(config_file)

    def test_raises_for_nonexistent_file(self, tmp_path):
        """Should raise FileNotFoundError for nonexistent file."""
        nonexistent = tmp_path / 'nonexistent.toml'

        with pytest.raises(FileNotFoundError):
            load_config(nonexistent)

    def test_loads_empty_config(self, tmp_path):
        """Should load empty config file."""
        config_file = tmp_path / 'keymap_align.toml'
        config_file.write_text('')

        result = load_config(config_file)
        assert result == {}


class TestResolveConfigLayout:
    """Tests for resolve_config_layout function."""

    def test_returns_none_when_no_layout(self, tmp_path):
        """Should return None when no layout in config."""
        config_file = tmp_path / 'keymap_align.toml'
        result = resolve_config_layout({}, config_file)
        assert result is None

    def test_returns_bundled_name_as_is(self, tmp_path):
        """Should return bundled layout name as-is."""
        config_file = tmp_path / 'keymap_align.toml'
        result = resolve_config_layout({'layout': 'corne42'}, config_file)
        assert result == 'corne42'

    def test_resolves_relative_path(self, tmp_path):
        """Should resolve relative path relative to config file."""
        config_file = tmp_path / 'keymap_align.toml'
        result = resolve_config_layout({'layout': './layouts/custom.json'}, config_file)

        expected = str((tmp_path / 'layouts' / 'custom.json').resolve())
        assert result == expected

    def test_preserves_absolute_path(self, tmp_path):
        """Should preserve absolute paths."""
        config_file = tmp_path / 'keymap_align.toml'
        result = resolve_config_layout({'layout': '/absolute/path/layout.json'}, config_file)
        assert result == '/absolute/path/layout.json'

    def test_detects_path_with_json_extension(self, tmp_path):
        """Should detect paths by .json extension."""
        config_file = tmp_path / 'keymap_align.toml'
        result = resolve_config_layout({'layout': 'custom_layout.json'}, config_file)

        # Should be resolved as a path (relative to config)
        expected = str((tmp_path / 'custom_layout.json').resolve())
        assert result == expected

    def test_handles_nested_config_path(self, tmp_path):
        """Should handle relative paths from nested config locations."""
        nested = tmp_path / 'project' / 'config'
        nested.mkdir(parents=True)
        config_file = nested / 'keymap_align.toml'

        result = resolve_config_layout({'layout': '../layouts/my.json'}, config_file)

        expected = str((nested.parent / 'layouts' / 'my.json').resolve())
        assert result == expected
