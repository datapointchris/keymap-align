"""Command-line interface for keymap-align."""

import importlib.metadata
import sys
from pathlib import Path
from typing import Annotated

import typer
from pyselfupdate import Config
from pyselfupdate import notify
from pyselfupdate.typercmd import run_update

from keymap_align.align import align_keymap_with_layout
from keymap_align.config import find_config_file
from keymap_align.config import get_align_config
from keymap_align.config import load_config
from keymap_align.layout_resolver import get_bundled_layout_names
from keymap_align.layout_resolver import resolve_layout

ROOT_HELP = (
    "Align a ZMK keymap so its bindings sit in columns matching the keyboard's physical shape. "
    '`format` is the command to run, by hand or from an editor formatter. It rewrites the keymap '
    'in place, taking the layout from a flag or from a keymap_align.toml beside the keymap. '
    '`layouts list` names the boards that ship with the tool, which is what `format --layout` accepts.'
    '\n\n'
    'Run any partial command with no arguments or --help to see what comes next.'
)

ROOT_EPILOG = """
Examples:

[b]keymap-align format -k corne.keymap --layout corne42[/b] — align a keymap for a board that ships with the tool

[b]keymap-align layouts list[/b] — the boards --layout accepts
"""

FORMAT_HELP = (
    "Align a ZMK keymap so its bindings sit in columns matching the keyboard's physical shape. "
    'The layout is what tells the aligner where the physical gaps are, so every run needs one: '
    'name a bundled board with --layout, point at your own with --layout-file, or let a '
    'keymap_align.toml beside the keymap supply it. A flag beats the config file. '
    'Without --output the keymap is rewritten in place.'
)

FORMAT_EPILOG = """
Examples:

[b]keymap-align format -k corne.keymap --layout corne42[/b] — a board that ships with the tool

[b]keymap-align format -k corne.keymap[/b] — layout named by keymap_align.toml beside the keymap

[b]keymap-align format -k corne.keymap -l split34.json[/b] — a layout this repo owns

[b]keymap-align format -k corne.keymap -o aligned.keymap[/b] — write elsewhere, leave the original
"""

# One config for `update` and the notice, so the notice never names a release `update` would not install.
UPDATE_CONFIG = Config(tool='keymap-align', owner='datapointchris')

app = typer.Typer(
    name='keymap-align',
    no_args_is_help=True,
    help=ROOT_HELP,
    epilog=ROOT_EPILOG,
    add_completion=False,
    context_settings={'help_option_names': ['-h', '--help']},
)
layouts_app = typer.Typer(
    name='layouts',
    no_args_is_help=True,
    help='The keyboard layouts that ship with the tool, each one a name `format --layout` accepts.',
)
app.add_typer(layouts_app, name='layouts')


def show_version(asked: bool) -> None:
    if not asked:
        return
    try:
        version = importlib.metadata.version('keymap-align')
    except importlib.metadata.PackageNotFoundError:
        version = 'unknown'
    print(f'keymap-align {version}')
    raise typer.Exit()


@app.callback()
def root(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option('--version', callback=show_version, is_eager=True, help='Show the installed version and exit.'),
    ] = None,
) -> None:
    # `update` is already installing the release the notice would name.
    if ctx.invoked_subcommand != 'update':
        notify(UPDATE_CONFIG)


@app.command('format', help=FORMAT_HELP, short_help="Align a keymap's bindings into the columns of a layout.", epilog=FORMAT_EPILOG)
def format_keymap(
    keymap: Annotated[
        str,
        typer.Option('--keymap', '-k', help='The .keymap file to align.', rich_help_panel='Input'),
    ],
    layout: Annotated[
        str | None,
        typer.Option('--layout', help='Bundled layout name, e.g. corne42.', rich_help_panel='Layout'),
    ] = None,
    layout_file: Annotated[
        str | None,
        typer.Option('--layout-file', '-l', help='Layout JSON to use instead of a bundled one.', rich_help_panel='Layout'),
    ] = None,
    output: Annotated[
        str | None,
        typer.Option('--output', '-o', help='Write here instead of rewriting the keymap in place.', rich_help_panel='Output'),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option('--debug', help='Show the column math behind each alignment decision.', rich_help_panel='Output'),
    ] = False,
) -> None:
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
        layout_context = resolve_layout(layout, layout_file, align_config.layout)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        raise typer.Exit(1) from e

    with layout_context as layout_path:
        success = align_keymap_with_layout(
            keymap,
            layout_path,
            output,
            debug,
            indent_size=align_config.indent_size,
            padding=align_config.padding,
        )
    raise typer.Exit(0 if success else 1)


@layouts_app.command('list')
def list_layouts() -> None:
    """Print the name of every bundled layout, one per line."""
    for name in get_bundled_layout_names():
        print(name)


@app.command(rich_help_panel='Manage')
def update(
    check_only: Annotated[bool, typer.Option('--check', help='Report whether an update is available without installing it.')] = False,
) -> None:
    """Update keymap-align to the latest release."""
    run_update(UPDATE_CONFIG, check_only=check_only)


if __name__ == '__main__':
    app()
