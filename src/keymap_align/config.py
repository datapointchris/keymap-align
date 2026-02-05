"""Config file discovery and loading for keymap-align."""

import subprocess  # nosec B404
import tomllib
from pathlib import Path


def _get_git_root(start_path: Path) -> Path | None:
    """Get the git repository root for a path, if it exists."""
    try:
        result = subprocess.run(  # nosec B603, B607
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=start_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def find_config_file(start_path: Path) -> Path | None:
    """Search up directory tree for keymap_align.toml.

    Stops at git root or filesystem root.

    Args:
        start_path: Directory to start searching from

    Returns:
        Path to config file if found, None otherwise
    """
    start_path = start_path.resolve()
    git_root = _get_git_root(start_path)

    current = start_path
    while True:
        config_path = current / 'keymap_align.toml'
        if config_path.is_file():
            return config_path

        # Stop at git root if we have one
        if git_root and current == git_root:
            break

        # Stop at filesystem root
        parent = current.parent
        if parent == current:
            break

        current = parent

    return None


def load_config(config_path: Path) -> dict:
    """Load and parse keymap_align.toml.

    Args:
        config_path: Path to the config file

    Returns:
        Parsed config dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        tomllib.TOMLDecodeError: If config file is invalid TOML
    """
    with config_path.open('rb') as f:
        return tomllib.load(f)


def resolve_config_layout(config: dict, config_path: Path) -> str | None:
    """Resolve layout value from config.

    If layout is a relative path, resolve relative to config file location.
    If layout is a name (no path separators), return as-is (bundled lookup).

    Args:
        config: Parsed config dictionary
        config_path: Path to the config file (for resolving relative paths)

    Returns:
        Layout value (name or resolved path), or None if not specified
    """
    layout = config.get('layout')
    if layout is None:
        return None

    # Check if it's a path (contains separator or .json extension)
    if '/' in layout or '\\' in layout or layout.endswith('.json'):
        # It's a path - resolve relative to config file location
        layout_path = Path(layout)
        if not layout_path.is_absolute():
            layout_path = config_path.parent / layout_path
        return str(layout_path.resolve())

    # It's a bundled layout name - return as-is
    return layout
