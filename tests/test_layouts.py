"""Tests for the layouts module."""

import pytest

from keymap_align.layout_resolver import get_bundled_layout_names
from keymap_align.layout_resolver import get_bundled_layout_path
from keymap_align.layout_resolver import resolve_layout


class TestGetBundledLayoutNames:
    """Tests for get_bundled_layout_names function."""

    def test_returns_list(self):
        """Should return a list."""
        result = get_bundled_layout_names()
        assert isinstance(result, list)

    def test_contains_expected_layouts(self):
        """Should contain the bundled layouts."""
        result = get_bundled_layout_names()
        assert 'corne42' in result
        assert 'piantor' in result
        assert 'glove80' in result

    def test_returns_sorted_list(self):
        """Should return layouts in sorted order."""
        result = get_bundled_layout_names()
        assert result == sorted(result)


class TestGetBundledLayoutPath:
    """Tests for get_bundled_layout_path function."""

    def test_returns_path_for_valid_layout(self):
        """Should return a path for valid layout names."""
        path = get_bundled_layout_path('corne42')
        assert path.exists()
        assert path.name == 'corne42.json'

    def test_all_bundled_layouts_exist(self):
        """All bundled layouts should have valid paths."""
        for name in get_bundled_layout_names():
            path = get_bundled_layout_path(name)
            assert path.exists(), f'Layout {name} should exist'
            assert path.suffix == '.json'

    def test_raises_for_invalid_layout(self):
        """Should raise ValueError for unknown layout names."""
        with pytest.raises(ValueError) as exc_info:
            get_bundled_layout_path('nonexistent_layout')

        assert 'nonexistent_layout' in str(exc_info.value)
        assert 'Available:' in str(exc_info.value)


class TestResolveLayout:
    """Tests for resolve_layout function."""

    def test_layout_file_takes_precedence(self):
        """--layout-file should take precedence over other options."""
        result = resolve_layout(
            layout_arg='corne42',
            layout_file_arg='/custom/path.json',
            config_layout='piantor',
        )
        assert result == '/custom/path.json'

    def test_layout_arg_takes_precedence_over_config(self):
        """--layout should take precedence over config."""
        result = resolve_layout(
            layout_arg='corne42',
            layout_file_arg=None,
            config_layout='piantor',
        )
        assert 'corne42.json' in result

    def test_config_layout_used_when_no_args(self):
        """Config layout should be used when no CLI args provided."""
        result = resolve_layout(
            layout_arg=None,
            layout_file_arg=None,
            config_layout='glove80',
        )
        assert 'glove80.json' in result

    def test_raises_when_no_layout_specified(self):
        """Should raise ValueError when no layout is specified."""
        with pytest.raises(ValueError) as exc_info:
            resolve_layout(
                layout_arg=None,
                layout_file_arg=None,
                config_layout=None,
            )
        assert 'No layout specified' in str(exc_info.value)

    def test_path_like_value_treated_as_path(self):
        """Values with / or .json should be treated as paths."""
        result = resolve_layout(
            layout_arg='/some/layout.json',
            layout_file_arg=None,
            config_layout=None,
        )
        assert result == '/some/layout.json'

    def test_config_path_value_treated_as_path(self):
        """Config values with path separators should be treated as paths."""
        result = resolve_layout(
            layout_arg=None,
            layout_file_arg=None,
            config_layout='./layouts/custom.json',
        )
        assert result == './layouts/custom.json'

    def test_bundled_name_resolved_to_path(self):
        """Bundled layout names should resolve to actual paths."""
        result = resolve_layout(
            layout_arg='piantor',
            layout_file_arg=None,
            config_layout=None,
        )
        from pathlib import Path

        path = Path(result)
        assert path.exists()
        assert path.name == 'piantor.json'
