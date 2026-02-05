"""Layout resolution for keymap-align.

Handles bundled layouts and layout path resolution.
"""

import importlib.resources
from pathlib import Path


def get_bundled_layout_names() -> list[str]:
    """Return list of bundled layout names (without .json extension)."""
    layouts_package = importlib.resources.files('keymap_align.layouts')
    names = [item.name[:-5] for item in layouts_package.iterdir() if item.name.endswith('.json')]
    return sorted(names)


def get_bundled_layout_path(name: str) -> Path:
    """Return path to bundled layout file.

    Args:
        name: Layout name without .json extension (e.g., 'corne42')

    Returns:
        Path to the bundled layout file

    Raises:
        ValueError: If layout name is not found in bundled layouts
    """
    layout_file = importlib.resources.files('keymap_align.layouts').joinpath(f'{name}.json')

    if not layout_file.is_file():
        available = get_bundled_layout_names()
        raise ValueError(f"Unknown bundled layout '{name}'. Available: {', '.join(available)}")

    # For importlib.resources, we need to get a concrete path
    # Using as_file context manager for resource access
    with importlib.resources.as_file(layout_file) as path:
        return Path(path)


def _is_file_path(value: str) -> bool:
    """Check if a value looks like a file path rather than a layout name."""
    return '/' in value or '\\' in value or value.endswith('.json')


def resolve_layout(
    layout_arg: str | None,
    layout_file_arg: str | None,
    config_layout: str | None,
) -> str:
    """Resolve layout to a file path based on precedence rules.

    Precedence: --layout-file > --layout > config > error

    If a value looks like a path (contains / or .json), treat as file path.
    Otherwise, look up as bundled layout name.

    Args:
        layout_arg: Value from --layout argument (bundled name or path)
        layout_file_arg: Value from --layout-file argument (explicit file path)
        config_layout: Value from config file (bundled name or path)

    Returns:
        Path to the layout file as a string

    Raises:
        ValueError: If no layout specified or layout not found
    """
    # Determine which value to use based on precedence
    if layout_file_arg is not None:
        # --layout-file is always a file path
        return layout_file_arg

    if layout_arg is not None:
        value = layout_arg
    elif config_layout is not None:
        value = config_layout
    else:
        raise ValueError(
            'No layout specified. Use --layout <name> for bundled layouts, '
            '--layout-file <path> for custom layouts, or create keymap_align.toml'
        )

    # Resolve the value - either as a path or bundled name
    if _is_file_path(value):
        return value
    # Bundled layout name
    return str(get_bundled_layout_path(value))
