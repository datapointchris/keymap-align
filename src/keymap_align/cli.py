"""Command-line interface for keymap-align."""

import sys
from pathlib import Path
from typing import Annotated

import typer

from keymap_align.align import align_keymap_with_layout
from keymap_align.config import find_config_file
from keymap_align.config import get_align_config
from keymap_align.config import load_config
from keymap_align.layout_resolver import get_bundled_layout_names
from keymap_align.layout_resolver import resolve_layout

EPILOG = """
Examples:

[b]keymap-align -k corne.keymap --layout corne42[/b] — a board that ships with the tool

[b]keymap-align -k corne.keymap[/b] — layout named by keymap_align.toml beside the keymap

[b]keymap-align -k corne.keymap -l split34.json[/b] — a layout this repo owns

[b]keymap-align -k corne.keymap -o aligned.keymap[/b] — write elsewhere, leave the original

[b]keymap-align --list-layouts[/b] — what --layout will accept
"""

HELP = (
    "Align a ZMK keymap so its bindings sit in columns matching the keyboard's physical shape. "
    'The layout is what tells the aligner where the physical gaps are, so every run needs one: '
    'name a bundled board with --layout, point at your own with --layout-file, or let a '
    'keymap_align.toml beside the keymap supply it. A flag beats the config file. '
    'Without --output the keymap is rewritten in place.'
)

app = typer.Typer(
    add_completion=False,
    context_settings={'help_option_names': ['-h', '--help']},
)


@app.command(help=HELP, epilog=EPILOG)
def main(
    keymap: Annotated[
        str | None,
        typer.Option('--keymap', '-k', help='The .keymap file to align.', rich_help_panel='Input'),
    ] = None,
    layout: Annotated[
        str | None,
        typer.Option('--layout', help='Bundled layout name, e.g. corne42.', rich_help_panel='Layout'),
    ] = None,
    layout_file: Annotated[
        str | None,
        typer.Option('--layout-file', '-l', help='Layout JSON to use instead of a bundled one.', rich_help_panel='Layout'),
    ] = None,
    list_layouts: Annotated[
        bool,
        typer.Option('--list-layouts', help='Print the bundled layout names and exit.', rich_help_panel='Layout'),
    ] = False,
    output: Annotated[
        str | None,
        typer.Option('--output', '-o', help='Write here instead of rewriting the keymap in place.', rich_help_panel='Output'),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option('--debug', help='Show the column maths behind each alignment decision.', rich_help_panel='Output'),
    ] = False,
):
    if list_layouts:
        for name in get_bundled_layout_names():
            print(name)
        raise typer.Exit(0)

    if not keymap:
        raise typer.BadParameter('required unless --list-layouts is given', param_hint='--keymap/-k')

    keymap_path = Path(keymap).resolve()
    config = {}
    config_path = find_config_file(keymap_path.parent)
    if config_path:
        try:
            config = load_config(config_path)
        except Exception as e:
            print(f'Warning: Failed to load config from {config_path}: {e}', file=sys.stderr)

    align_config = get_align_config(config, config_path)

    try:
        layout_path = resolve_layout(layout, layout_file, align_config.layout)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        raise typer.Exit(1) from e

    success = align_keymap_with_layout(
        keymap,
        layout_path,
        output,
        debug,
        indent_size=align_config.indent_size,
        padding=align_config.padding,
    )
    raise typer.Exit(0 if success else 1)


if __name__ == '__main__':
    app()
