"""Tests for the layouts module."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

import keymap_align
from keymap_align.layout_resolver import bundled_layout_path
from keymap_align.layout_resolver import get_bundled_layout_names
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


class TestBundledLayoutPath:
    """Tests for bundled_layout_path function."""

    def test_returns_path_for_valid_layout(self):
        """Should return a path for valid layout names."""
        with bundled_layout_path('corne42') as path:
            assert path.exists()
            assert path.name == 'corne42.json'

    def test_all_bundled_layouts_exist(self):
        """All bundled layouts should have valid paths."""
        for name in get_bundled_layout_names():
            with bundled_layout_path(name) as path:
                assert path.exists(), f'Layout {name} should exist'
                assert path.suffix == '.json'

    def test_raises_for_invalid_layout(self):
        """Should raise ValueError for unknown layout names."""
        with pytest.raises(ValueError) as exc_info:
            bundled_layout_path('nonexistent_layout')

        assert 'nonexistent_layout' in str(exc_info.value)
        assert 'Available:' in str(exc_info.value)

    def test_layout_is_readable_from_a_zipped_package(self, tmp_path):
        """A zipped package has no layout file on disk, so the path is a copy that must outlive the lookup."""
        package = Path(keymap_align.__file__).parent
        archive = tmp_path / 'keymap_align.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            for file in package.rglob('*'):
                if file.is_file() and '__pycache__' not in file.parts:
                    zipped.write(file, file.relative_to(package.parent))
        script = (
            'import json, sys\n'
            f'sys.path.insert(0, {str(archive)!r})\n'
            'import keymap_align.layout_resolver as resolver\n'
            'assert resolver.__file__.startswith(sys.path[0]), resolver.__file__\n'
            "with resolver.resolve_layout('corne42', None, None) as path:\n"
            "    print(json.loads(open(path).read())['name'])\n"
        )

        result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == json.loads((package / 'layouts' / 'corne42.json').read_text())['name']


class TestResolveLayout:
    """Tests for resolve_layout function."""

    def test_layout_file_takes_precedence(self):
        """--layout-file should take precedence over other options."""
        with resolve_layout(
            layout_arg='corne42',
            layout_file_arg='/custom/path.json',
            config_layout='piantor',
        ) as path:
            assert path == Path('/custom/path.json')

    def test_layout_arg_takes_precedence_over_config(self):
        """--layout should take precedence over config."""
        with resolve_layout(
            layout_arg='corne42',
            layout_file_arg=None,
            config_layout='piantor',
        ) as path:
            assert path.name == 'corne42.json'

    def test_config_layout_used_when_no_args(self):
        """Config layout should be used when no CLI args provided."""
        with resolve_layout(
            layout_arg=None,
            layout_file_arg=None,
            config_layout='glove80',
        ) as path:
            assert path.name == 'glove80.json'

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
        with resolve_layout(
            layout_arg='/some/layout.json',
            layout_file_arg=None,
            config_layout=None,
        ) as path:
            assert path == Path('/some/layout.json')

    def test_config_path_value_treated_as_path(self):
        """Config values with path separators should be treated as paths."""
        with resolve_layout(
            layout_arg=None,
            layout_file_arg=None,
            config_layout='./layouts/custom.json',
        ) as path:
            assert path == Path('./layouts/custom.json')

    def test_bundled_name_resolved_to_path(self):
        """Bundled layout names should resolve to actual paths."""
        with resolve_layout(
            layout_arg='piantor',
            layout_file_arg=None,
            config_layout=None,
        ) as path:
            assert path.exists()
            assert path.name == 'piantor.json'
